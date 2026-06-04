# Core test suite for the nlpsolver pipeline.
# Tests are organized by linguistic phenomenon, from simple to complex.
#
# Table of contents
#
# PHASE I: FOUNDATIONS
# FUNDAMENTAL TAXONOMY & TYPE LOGIC (10 tests)
# LOGICAL CONNECTIVES (13 tests)
# PROPERTIES & ADJECTIVAL LOGIC (38 tests)
# NUMBER & PLURALITY (14 tests)
#
# PHASE II: REFERENCE & POSSESSION
# COREFERENCE & ANAPHORA (95 tests)
# POSSESSION & HAVE (45 tests)
# DEFINITE DESCRIPTIONS: X OF Y AND POSSESSIVES (40 tests)
# POSSESSION INFERENCE FROM DESCRIPTIONS (127 tests)
# SETS AND COUNTING (28 tests)
# MEASURES (96 tests)
#
# PHASE III: QUANTIFIERS & COMPARISON
# QUANTIFIERS: UNIVERSAL & EXISTENTIAL (30 tests)
# QUANTIFIERS: PROPORTIONAL & NUMERIC (10 tests)
# COMPARATIVES & EQUALITY (8 tests)
#
# PHASE IV: MODIFICATION & STRUCTURE
# COORDINATION (NP, VP, CLAUSAL) (19 tests)
# LISTS AND CONJUNCTIONS (52 tests)
# INTERNAL MODIFICATION (77 tests)
# RELATIVE CLAUSES (269 tests)
# AMBIGUOUS MODIFIER SCOPE (36 tests)
#
# PHASE V: CLAUSE ALTERNATIONS
# PASSIVE VOICE (48 tests)
# SUBORDINATE CLAUSES (31 tests)
# ELLIPSIS & GAPPING (10 tests)
#
# PHASE VI: EVENTS & STATE
# ACTION MODES & HABITS (35 tests)
# TRANSFER OF POSSESSION (GIVE/TAKE) (35 tests)
# TENSE, ASPECT & CHANGE OF STATE (42 tests)
# SPATIAL LOGIC & WHERE QUERIES (95 tests)
# ACTION AND WORLD STATE SEQUENCES (12 tests)
#
# PHASE VII: QUESTIONS
# QUESTION LOGIC (WHO/WHAT/WHICH) (26 tests)
#
# PHASE VIII: REASONING
# IF-THEN INFERENCE (65 tests)
# DEFAULT & DEFEASIBLE REASONING (62 tests)
# DEFAULTS WITH EXCEPTIONS (BLOCKING) (11 tests)
# UNCERTAINTY & CONFIDENCE (83 tests)
# ADVANCED SEMANTIC OPERATORS (27 tests)
# COMPLEX REASONING CHAINS (11 tests)

[
# == FUNDAMENTAL TAXONOMY & TYPE LOGIC ==

  [1, 'Elephants are animals. Elephants are animals?', True],
  [2, 'Elephants are animals. John is an elephant. John is an animal?', True],
  [3, 'Elephants are not birds. John is an elephant. John is not a bird?', True],
  [4, 'Elephants are animals. John is an elephant. Who is an animal?', 'John.'],
  [5, 'Elephants are not birds. John is an elephant. John is a bird?', False],
  [6, 'Elephants are animals. Who is an animal?', 'An elephant.'],
  [7, 'Elephants are grey animals. John is an elephant. Who is grey?', 'John.'],
  [8, 'Elephants are big animals. John is an elephant. Who is nice?', None],
  [9, 'Elephants are big animals. John is a big animal. John is an elephant?', None],
  [10, 'Elephants are not birds. John is not a bird. John is an elephant?', None],

# == LOGICAL CONNECTIVES ==

  [11, 'John is a man or not a man?', True],
  [12, 'John is a man and not a man?', False],
  [13, 'John is tall or not tall?', True],
  [14, 'John is tall and not tall?', False],
  [15, 'John is a tall man and not a tall man?', False],
  [16, 'John has a car or does not have a car?', True],
  [17, 'John has a car and does not have a car?', False],
  [18, 'John has a car?', None],
  [19, 'John is in Estonia or is not in Estonia?', True],
  [20, 'John is in Estonia and is not in Estonia?', False],
  [21, 'John is in Estonia?', None],
  [22, 'John is glad. If John is glad, then Mike is not glad. Is Mike glad?', False],
  [23, 'If John is glad, then Mike is not glad. Is Mike glad?', None],

# == PROPERTIES & ADJECTIVAL LOGIC ==

  # -- adjective combos with and/or --

  [24, 'Big or strong elephants are nice. John is a big elephant. John is nice?', True],
  [25, 'Big or strong elephants are nice. John is a big elephant. John is strong. John is nice?', True],
  [26, 'Big or strong elephants are nice. John is an elephant. John is nice?', None],
  [27, 'Big and strong elephants are nice. John is a big elephant. John is a strong elephant. John is nice?', True],
  [28, 'Yellow and green elephants are nice. John is an elephant. John is yellow and green. John is nice?', "Probably true."],
  [29, 'Big and strong elephants are nice. John is a strong elephant. John is nice?', None],
  [30, 'Big and not strong elephants are nice. John is a big elephant. John is a not strong elephant. John is nice?', True],

  # -- degree modifiers: very, somewhat, extremely --

  [31, 'John is very big. John is extremely big?', True],
  [32, 'John is very big. John is very big?', True],
  [33, 'John is very big. John is big?', True],

  [34, 'John is big. John is very big?', None],
  [35, 'John is big. John is big?', True],
  [36, 'John is somewhat big. John is big?', True],
  [37, 'John is somewhat big. John is somewhat big?', True],
  [38, 'John is somewhat big. Mike is very big. Who is very big?', 'Mike'],
  [39, 'John is big. John is not big?', False],
  [40, 'John is very big. John is not very big?', False],
  [41, 'John is very big. John is not big?', False],
  [42, 'John is somewhat big. John is not somewhat big?', False],
  [43, 'John is not very big. John is very big?', False],
  [44, 'A not very big bear is nice. The bear is a very big bear?', False],
  [45, 'John is a not very big bear. John is a very big bear?', False],
  [46, 'John is not a very big bear. John is a very big bear?', False],

  [47, 'A very big mouse is nice. The mouse is a very big mouse?', True],
  [48, 'A very big mouse is nice. The mouse is a big mouse?', True],
  [49, 'A very big mouse is nice. The mouse is very big?', True],
  [50, 'A very big mouse is nice. The mouse is big?', True],

  # -- class-relative properties --

  [51, 'Frogs are small animals. John is a frog. John is a small animal?', True],
  [52, 'Frogs are small animals. John is a frog. John is small?', True],
  [53, 'Frogs are small. John is a frog. John is small?', True],
  [54, 'Frogs are small. John is a frog. John is a small animal?', None],

  [55, 'John is a big mouse. John is big?', True],
  [56, 'John is a big mouse. John is a big mouse?', True],
  [57, 'John is a big mouse. John is a big thing?', None],

  [58, 'The car is red. The car is red?', True],
  [59, 'The car is red. The car is nice?', None], 
  [60, ' The big mouse is strong. The mouse is a big mouse?', True],
  [61, 'The car is red. The bike is small. Is the bike red?', None],

# == NUMBER & PLURALITY ==

  # -- conjunction in have-objects --

  [62, 'Elephants have long trunks and short tails. John is an elephant. Who has a trunk and a tail?', 'John.'],
  [63, 'Elephants have long trunks and short tails. John is an elephant. Who has a long trunk and a short tail?', 'John.'],

  [64, 'Elephants have long trunks and no wings. John is an elephant. John has a wing?', False],
  [65, 'Elephants have long trunks and no wings. John is an elephant. John has no wing?', True],
  [66, 'Elephants have long trunks and no wings. John is an elephant. John does not have a wing?', True],
  [67, 'Elephants have long trunks and no wings. John is an elephant. Who does not have a wing?', ['John.', 'Elephants.']],
  [68, 'Elephants have long trunks and no wings. John is an elephant. John has a long trunk and no wing?', True],
  [69, 'Elephants have long trunks and no wings. John is an elephant. John is long?', None],

  # -- disjunction in have-objects --

  [70, 'Elephants have trunks or tails. John is an elephant. John has no trunk. John has a tail?', True],
  [71, 'Elephants have either trunks or tails. John is an elephant. John has a tail and a trunk?', False],
  [72, 'Elephants have trunks or tails. John is an elephant. John has a tail or a trunk?', True],

  [73, 'Elephants have long or short trunks. John is an elephant. John does not have a long trunk. John has a short trunk?', True],
  [74, 'Elephants have long or short trunks. John is an elephant. John has a trunk?', True],
  [75, 'Elephants have long or short trunks. John is an elephant. John has a long trunk?', None],

# == COREFERENCE & ANAPHORA ==

  # -- basic property assertions --

  [76, 'John was yellow. John was yellow?', True],
  [77, 'John was yellow. John was nice?', None],
  [78, 'John was yellow. A man was nice?', None],

  [79, 'A man was yellow. A man was yellow?', True],
  [80, 'A man was yellow. A man was nice?', None],
  [81, 'A man was yellow. John was nice?', None],

  # -- definite descriptions --


  # -- definite description resolution --

  [82, 'An elephant was strong. An animal lifted a stone. Who lifted the stone?', ['The animal', 'The strong elephant', 'The elephant']],
  [83, 'An elephant was strong. The nice animal lifted a stone. Who lifted the stone?', ['The nice animal', 'The elephant.']],
  [84, 'An elephant was strong. The animal lifted a stone. Who lifted the stone?', 'The elephant'],
  [85, 'A nice elephant was strong. The nice animal lifted a stone. Who lifted the stone?', 'The nice elephant'],
  [86, 'A nice elephant was strong. A mouse was white. The white animal lifted the stone. Who lifted the stone?', 'The mouse'],
  [87, 'A nice elephant was strong. A flower was white. The animal lifted the stone. Who lifted the stone?', ['The nice elephant', 'The elephant.', 'The animal.']],
  [88, 'An old nice grey elephant was strong. The nice animal lifted a stone. Who lifted the stone?', ['The old nice grey elephant', 'The elephant.']],

  [89, 'A big old grey elephant was strong. The big animal lifted a stone. The stone was red. The old animal lifted a red stone?', True],
  [90, 'A big old grey elephant was strong. The big animal lifted a stone. The stone was heavy. The old animal lifted a heavy stone?', True],
  [91, 'A big old grey elephant was strong. The big animal lifted a stone. It was red. The grey animal lifted what?', ['The stone', 'A red stone.']],

  # -- determiners: a/the --


  # -- distinct indefinites --

  [92, 'A red car is big. A new car is small. A car is old?', None],
  [93, 'A red car is big. A new car is nice. Some car is red and big?', True],
  [94, 'A red car is big. A new car is nice. A car is red and nice?', None],
  [95, 'A red car is big. A new car is nice. The red car is big?', True],
  [96, 'A red car is big. A new car is nice. The new car is nice?', True],

  [97, 'A red car is big. The red car is strong. The car is red and strong?', True],
  [98, 'A red car is big. The car is strong. The car is red and strong?', True],
  [99, 'A red car is big. The car is strong. A car is black?', None],

  # -- pronoun resolution (he/she/it) --

  [100, 'Mary saw John. She was nice. Who was nice?', 'Mary'],
  [101, 'Mary saw John. He was nice. Who was nice?', 'John'],
  [102, 'John saw Mary. She was nice. Who was nice?', 'Mary'],
  [103, 'John saw Mary. He was nice. Who was nice?', 'John'],

  [104, 'A mother saw a man. She was nice. Who was nice?', ['The mother', 'The nice mother']],
  [105, 'A mother saw a man. He was nice. Who was nice?', ['The man', 'The nice man']],
  [106, 'A boy saw a girl. She was nice. Who was nice?', ['The girl', 'The nice girl']],
  [107, 'A boy saw a girl. He was nice. Who was nice?', ['The boy', 'The nice boy']],
  [108, 'A mother saw a fox. It was nice. Who was nice?', ['The fox', 'The nice fox']],
  [109, 'A mother saw a fox. She was nice. Who was nice?', ['The mother', 'The nice mother']],
  [110, 'A fox saw a mother. She was nice. Who was nice?', ['The mother', 'The fox.', 'The nice mother']],
  [111, 'A mother saw a fox. He was nice. Who was nice?', ['The fox', 'The nice fox']],
  [112, 'A fox saw a mother. He was nice. Who was nice?', ['The fox', 'The nice fox']],
  [113, 'A fox saw a mother. It was nice. Who was nice?', ['The fox', 'The mother.', 'The nice mother']],

  # -- names and non-names --

  [114, 'Muggles cannot disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?', False],
  [115, 'Muggles can not disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?', False],
  [116, 'Americans cannot disappear. Mr Dursley is an American. Mr Dursley can disappear?', False],
  [117, 'Americans can not disappear. Mr Dursley is an American. Mr Dursley can disappear?', False],
  [118, 'Catholics can not disappear. Mr Dursley is a catholic. Mr Dursley can disappear?', False],

  # -- true as adjective vs truth value --

  [119, 'Sue is a true patriot. Sue is a true patriot?', True],
  [120, 'Sue is a true patriot. Sue is a nice patriot?', None],
  [121, 'Sue is a true patriot. Sue is a true driver?', None],

  [122, 'The elephants saw a fox. They were nice. The elephants were nice?', True],
  [123, 'The elephants saw a fox. They were nice. The fox was nice?', None],
  [124, 'The elephants saw a fox. They were nice. Who were nice?', 'The elephants'],
  [125, 'The elephants saw a fox. It was nice.  The fox was nice?', True],
  [126, 'The elephants saw a fox. It was nice.  The elephants were nice?', None],

  [127, 'The fox saw the elephants. They were nice. The elephants were nice?', True],
  [128, 'The fox saw the elephants. They were nice. The fox was nice?', None],
  [129, 'The fox saw the elephants. It was nice.  The elephants were nice?', None],

  # -- she/he pronoun resolution --

  [130, 'Mary was in a room. She was in the room?', True],
  [131, 'Mary was in a room. She was in a room?', True],
  [132, 'Mary was in a room. She was not in the room?', False],
  [133, 'She was in a room. She was in the room?', True],

  [134, 'An apple was bad. She was in a room. She was in the room?', True],
  [135, 'An apple was bad and she was in a room. She was in the room?', True],
  [136, 'An apple was bad. She was in a room. An apple was in a room?', None],
  [137, 'An apple was bad and she was in a room. An apple was in a room?', None],

  [138, 'John was bad. She was in a room. John was in a room?', None],
  [139, 'She was in a room. Who was in the room?', 'She'],

  # -- these/they anaphora --

  [140, 'The aunts saw shoes. These were nice. What was nice?', 'The shoes'],
  [141, 'A car had a dent. This was deep. What was deep?', 'A dent'],
  [142, 'A car had a dent. It was fast. What was fast?', 'The car'],

  # -- definite/indefinite coreference --

  [143, 'A gray elephant was nice. A white elephant was nice. The elephant was cool. The white elephant was cool?', True],
  [144, 'A gray elephant was nice. A white elephant was nice. The elephant was cool. The gray elephant was cool?', None],
  [145, 'A gray elephant was nice. A white elephant was nice. It was cool. The white elephant was cool?', True],
  [146, 'A gray elephant was nice. A white elephant was nice. It was cool. The gray elephant was cool?', None],

  # -- pronouns, reflexives, reciprocals --


  [147, 'Mike ate berries in the forest bought by Mary. Mike ate berries in the forest bought by Mary?', True],
  [148, 'Mike ate berries in the forest bought by Mary. Mike ate berries in the forest bought by John?', None],
  [149, 'Bears ate berries in the forest bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  [150, 'Bears ate berries in the forest bought by Mary. Bears ate berries in the forest bought by John?', None],

  # -- reflexives --

  [151, 'John saw himself in the mirror. Who did John see?', ['John.', 'Himself.']],
  [152, 'John saw himself in the mirror. Did Mary see John in the mirror?', None],
  [153, 'The boy lost his backpack. Who does the backpack belong to?', 'The boy.'],
  [154, 'The boy lost his backpack. Did the boy find his backpack?', None],
  [155, 'The students brought their books. Whose books were they?', ["The students'.", 'The students.']],
  [156, 'John saw himself in the mirror. John saw John?', True],
  [157, 'John saw himself in the mirror. Did John see Mary?', None],
  [158, 'Mary blamed herself. Mary blamed Mary?', True],
  [159, 'Tom washed himself. Tom washed Tom?', True],
  [160, 'Tom washed himself. Did Tom wash Mary?', None],
  [161, 'Eve introduced herself. Eve introduced Eve?', True],
  [162, 'Eve introduced Mary. Mary introduced Eve?', None],

  # -- reciprocals --

  [163, 'John and Mary saw each other. John saw Mary?', True],
  [164, 'John and Mary saw each other. Mary saw John?', True],
  [165, 'John and Mary saw each other. Did John see Eve?', None],

  [166, 'Tom and Eve greeted each other. Tom greeted Eve?', True],
  [167, 'Tom and Eve greeted each other. Eve greeted Tom?', True],
  [168, 'Tom and Eve greeted each other. Did Tom greet Mary?', None],

  [169, 'The boys helped themselves. The boys helped the boys?', True],
  [170, 'The girls admired themselves. The girls admired the girls?', True],


# == POSSESSION & HAVE ==

  # -- basic have --

  [171, 'Elephants have trunks. Elephants have trunks?', True],
  [172, 'No elephant has wings. No elephant has wings?', True],

  [173, 'No elephants have wings. Some elephant has wings?', False],
  [174, 'Elephants have no wings. Some elephant has wings?', False],
  [175, 'Elephants have no wings. John has no wings?', None],

  # -- have with quantifiers and negation --

  [176, 'All elephants have no wings. Some elephant has wings?', False],
  [177, 'All elephants have no wings. John has no wings?', None],
  [178, 'Some elephants have no wings. Some elephant has wings?', None],
  [179, 'Some elephants have no wings. John has no wings?', None],
  [180, 'No elephants have wings. All elephants do not have wings?', True],

  [181, 'Elephants have trunks. John has a trunk?', None],
  [182, 'All elephants have trunks. John has a trunk?', None],
  [183, 'Some elephants have trunks. John has a trunk?', None],

  [184, 'Elephants have a trunk. Birds have a trunk?', None],
  [185, 'Elephants have a trunk. Birds do not have a trunk?', None],

  # -- have with adjective-modified objects --

  [186, 'Elephants have long trunks. John is an elephant. John has a trunk?', True],
  [187, 'Elephants have no trunks. John is an elephant. John has a trunk?', False],

  [188, 'Elephants have long grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  [189, 'Elephants have long and grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  [190, 'Elephants have long grey trunks. John is an elephant. Who has a grey trunk?', 'John.'],
  [191, 'Elephants have long and grey trunks. John is an elephant. Who has a grey trunk?', 'John.'],
  [192, 'Elephants have long grey trunks. John is an elephant. Who has a long red trunk?', None],

  [193, 'Elephants have no long red trunks. John is an elephant. John has a long red trunk?', False],
  [194, 'Elephants have no long red trunks. John is an elephant. John has a long trunk?', None],

  # -- have with negated adjectives --

  [195, ' Elephants have not red trunks. John is an elephant. John has a not red trunk?', True],
  [196, ' Elephants have not red trunks. John is an elephant. John has a trunk?', True],
  [197, ' Elephants have not red trunks. John is an elephant. John has a big trunk?', None],

  [198, ' Elephants have long not red trunks. John is an elephant. John has a long not red trunk?', True],
  [199, ' Elephants have long not red trunks. John is an elephant. John has a long trunk?', True],
  [200, ' Elephants have long not red trunks. John is an elephant. John has a long black trunk?', None],
  [201, ' Elephants have long not red trunks. John is an elephant. John has a not red trunk?', True],

  [202, ' Elephants have long not big trunks. John is an elephant. John has a long not big trunk?', True],
  [203, ' Elephants have long not big trunks. John is an elephant. John has a not big trunk?', True],
  [204, ' Elephants have long not red trunks. John is an elephant. John has a long not small trunk?', None],
  [205, ' Elephants have long not big trunks. John is an elephant. John has a long trunk?', True],

  # -- do not have --

  [206, 'Elephants do not have long red trunks. John is an elephant. John has a long red trunk?', False],
  [207, 'Elephants do not have wings. John is an elephant. John has wings?', False],
  [208, 'Elephants do not have wings. John is an elephant. John has a wing?', False],
  [209, 'Elephants do not have long red wings. John is an elephant. John has a wing?', None],
  [210, 'John has cars. John has cars?', True],
  [211, 'John has blue cars. John has a car?', True],
  [212, 'John has blue cars. John has a blue car?', True],
  [213, 'Animals have legs. Animal has a leg?', True],

  [214, 'Elephants have long trunks. John is an elephant. Who has a trunk?', 'John.'],
  [215, 'Elephants have long trunks. John is an elephant. Who has a wheel?', None],

# == DEFINITE DESCRIPTIONS: X OF Y AND POSSESSIVES ==

  # -- X of Y in instrument phrases --

  [216, 'John ate berries with the edge of a spoon. John ate berries with the edge of a spoon?', True],
  [217, 'John ate berries with an edge of a spoon. John ate berries with an edge of a spoon?', True],
  [218, 'John ate berries with the edge of a spoon. John ate berries with the edge of a fork?', None],
  [219, 'John ate berries with the edge of a spoon. John ate berries with the tip of a spoon?', None],
  [220, 'John ate berries with an edge of a spoon. John ate berries with an edge?', True],
  [221, 'John ate berries with an edge of a spoon. John ate berries with a tip?', None],
  [222, 'John ate berries with an edge of a spoon. A spoon had an edge?', True],
  [223, 'John ate berries with an edge of a spoon. The spoon had the edge?', True],
  [224, 'John ate berries with the edge of the spoon. The spoon had the edge?', True],
  [225, 'John ate berries with the edge of the spoon. The spoon had the tip?', None],
  [226, 'John ate berries with the edge of a spoon. Berries have an edge?', None],

  # -- possessive 's constructions --

  [227, "John's brother has a car. John's brother has a car?", True],
  [228, "John's brother has a car. John's sister has a car?", None],
  [229, "Mary's sister owns a house. Who owns a house?", "Mary's sister."],
  [230, "John's brother's car is red. John's brother has a car?", True],
  [231, "John's brother's car is red. John's brother's car is blue?", False],
  [232, "Mary's uncle's bicycle is blue. Mary's uncle has a bicycle?", True],
  [233, "Mary's uncle's bicycle is blue. Mary's aunt has a bicycle?", None],

  # -- nested possessives --

  [234, "The roof of John's house is green. John has a house?", True],
  [235, "The handle of Mary's suitcase broke. Mary had a suitcase?", True],
  [236, "The handle of Mary's suitcase broke. Did the suitcase break?", None],

  # -- chained of-possessives --

  [237, 'The door of the house of John was open. John had a house?', True],
  [238, 'The door of the house of John was open. Was the door closed?', False],
  [239, 'The tail of the dog of Mary was short. Mary had a dog?', True],
  [240, "The color of John's car was black. John had a car?", True],
  [241, "The color of John's car was black. John had a truck?", None],
  [242, 'The owner of the horse of Mike smiled. Mike had a horse?', True],
  [243, 'The brother of the friend of Eve arrived. Eve had a friend?', True],
  [244, "The brother of the friend of Eve arrived. Did Eve's friend arrive?", None],
  [245, "John saw the mother of the boy. John saw a boy's mother?", True],
  [246, "John's sister laughed. Who has a sister?", 'John.'],
  [247, "John's sister laughed. Did John's brother laugh?", None],
  [248, "Mary's uncle arrived. Who has an uncle?", 'Mary.'],
  [249, 'The bicycle of Tom was new. Who had a bicycle?', 'Tom.'],
  [250, 'The bicycle of Tom was new. Was the bicycle old?', False],
  [251, 'The toy of the child was broken. Who had a toy?', ['The child.', 'A child.']],
  [252, 'The toy of the child was broken. Was the toy intact?', False],
  [253, 'John does not eat a carrot. John does not eat a carrot?', True],
  [254, 'John does not eat a carrot. John eats a carrot?', False],
  [255, 'John is not in a cave. John is not in a cave?', True],

# == POSSESSION INFERENCE FROM DESCRIPTIONS ==

  # -- the X of Y: property queries --

  [256, 'The head of Mary is clean. The head of Mary is clean?', True],
  [257, 'The head of Mary is clean. A head of Mary is clean?', True],
  [258, 'The head of Mary is clean. A head of Mike is clean?', None],
  [259, 'The head of Mary is clean. The head is clean?', True],

  [260, 'The car of Mary is clean. The car of Mike is clean?', None],

  [261, 'A leg of Mary is clean. A leg of Mary is clean?', True],
  [262, 'A leg of Mary is clean. A leg of Mary is long?', None],
  [263, 'A leg of Mary is clean. A leg of Mike is clean?', None],

  [264, "Mary's head is clean. Mary's head is clean?", True],
  [265, "Mary's head is clean. A head of Mary is clean?", True],
  [266, "Mary's head is clean. A head of Mike is clean?", None],
  [267, "Mary's head is clean. The head is clean?", True],

  [268, "Mary's leg is clean. A leg of Mary is clean?", True],
  [269, "Mary's leg is clean. A leg of Mary is long?", None],
  [270, "Mary's leg is clean. A leg of Mike is clean?", None],

  # -- possessive -> have inference --

  [271, "Mary's car is clean. Mary has a car?", True],
  [272, "Mary's car is clean. Mary has a clean car?", True],
  [273, "Mary's car is clean. Mary has a red car?", None],
  [274, "Mary's car is clean. Mary has a clean bike?", None],

  [275, "Elephant's head is green. John is an elephant. John has a head. John has a green head?", True],
  [276, 'The head of every elephant is green. John is an elephant. John has a green head?', True],
  [277, "Big elephant's head is green. John is an elephant. John has a head. John has a green head?", None],
  [278, 'A head of an elephant is green. An elephant has a green head?', True],

  [279, 'A head of an elephant is green. All elephants have a head. An elephant has a green head?', True],
  [280, 'A head of an elephant is green. Elephants have a head. An elephant has a green head?', True],

  # -- generic possessives --

  [281, "Elephant's head is green. Elephant's head is green?", 'Probably true'],
  [282, 'The head of Mary is clean. Mary has a clean head?', True],

  [283, 'The car of Mary is clean. Mary has a car?', True],
  [284, 'The car of Mary is clean. Mike has a car?', None],
  [285, 'The car of Mary is clean. Mary has a clean car?', True],
  [286, 'The car of Mary is clean. Mary has a red car?', None],
  [287, 'The car of Mary is clean. Mary has a clean bike?', None],

  # -- saw X of Y --

  [288, 'John saw the head of Mary. John saw the head of Mary?', True],
  [289, 'John saw the head of Mary. John saw a head of Mary?', True],
  [290, 'John saw the head of Mary. John saw the head of Mike?', None],
  [291, 'John saw the head of Mary. John saw a head?', True],
  [292, 'John saw the head of Mary. John saw the hands of Mary?', None],

  [293, 'John saw the car of Mary. Mary had a car?', True],

  [294, 'John saw the head of the elephant. John saw the head of the elephant?', True],
  [295, 'John saw the head of the elephant. John saw the head?', True],
  [296, 'John saw the head of the elephant. John saw a head?', True],
  [297, 'John saw the head of the elephant. John saw the tail of the elephant?', None],
  [298, 'John saw the head of the elephant. John saw a nice head?', None],
  [299, 'John saw a head of an elephant. John saw a head of an elephant?', True],
  [300, 'John saw a head of an elephant. John saw the head?', True],
  [301, 'John saw a head of an elephant. John saw a head?', True],
  [302, 'John saw a head of an elephant. John saw the tail of the elephant?', None],
  [303, 'John saw a head of an elephant. John saw a tail of an elephant?', None],
  [304, 'John saw a head of an elephant. John saw a nice head?', None],

  # -- saw possessive-'s --

  [305, "John saw Mary's head. John saw Mary's head?", True],
  [306, "John saw Mary's head. John saw a head of Mary?", True],
  [307, "John saw Mary's head. John saw Mike's head?", None],
  [308, "John saw Mary's head. John saw the head of Mike?", None],
  [309, "John saw Mary's head. John saw a head?", True],
  [310, "John saw Mary's head. John saw the hands of Mary?", None],

  [311, "John saw Mary's car. Mary had a car?", True],

  [312, "John saw Mary's clean car. Mary had a clean car?", True],
  [313, "John saw Mary's clean car. Mary had a red car?", None],
  [314, "John saw Mary's clean car. Mary had a clean bike?", None],

  # -- saw generic possessives --

  [315, "John saw elephant's head. John saw elephant's head?", True],
  [316, "John saw elephant's head. John saw the head?", True],
  [317, "John saw elephant's head. John saw a head of an elephant?", True],
  [318, "John saw elephant's head. John saw a head of a tiger?", None],
  [319, "John saw elephant's head. John saw a head?", True],
  [320, "John saw elephant's head. John saw the tail of the elephant?", None],
  [321, "John saw elephant's head. John saw a nice head?", None],

  # -- a-vs-the in of-phrases --

  [322, 'John saw a head of an elephant. John saw a head of the elephant?', True],
  [323, 'John saw a head of the elephant. John saw a head of the elephant?', True],
  [324, 'John saw a head of the elephant. John saw a head of an elephant?', True],
  [325, 'John saw a head of an elephant. John saw a head of the bear?', None],
  [326, 'John saw a head of an elephant. John saw a head of a bear?', None],
  [327, 'John saw a head of the elephant. John saw a head of the bear?', None],
  [328, 'John saw a head of the elephant. John saw a head of a bear?', None],
  [329, 'John saw a head of an elephant. John saw a tail of the elephant?', None],
  [330, 'John saw a head of the elephant. John saw a tail of the elephant?', None],
  [331, 'John saw a head of the elephant. John saw a tail of an elephant?', None],

  [332, 'John saw a twig of an elephant. The elephant had a twig?', True],
  [333, 'John saw a twig of an elephant. The elephant had a spoon?', None],
  [334, 'John saw a twig of an elephant. An elephant had a twig?', True],
  [335, 'John saw a twig of an elephant. An elephant had a spoon?', None],
  [336, 'John saw the twig of an elephant. The elephant had a twig?', True],

  # -- observation implies possession --

  [337, 'John saw the twig of an elephant. The elephant had the twig?', True],
  [338, 'John saw the twig of an elephant. The elephant had a spoon?', None],

  # -- colored X of colored Y --

  [339, 'John saw a blue head of a red elephant. John saw a blue head of a red elephant?', True],
  [340, 'John saw a blue head of a red elephant. John saw a blue head?', True],
  [341, 'John saw a blue head of a red elephant. John saw the blue head?', True],
  [342, 'John saw a blue head of a red elephant. John saw the head?', True],
  [343, 'John saw a blue head of a red elephant. John saw a blue tail?', None],
  [344, 'John saw a blue head of a red elephant. John saw a head of an elephant?', True],
  [345, 'John saw a blue head of a red elephant. John saw a head of the red elephant?', True],

  # -- of-phrases in event descriptions --

  [346, 'The hand of a man moved a wheel. The hand of a man moved a wheel?', True],
  [347, 'The hand of a man moved a wheel. The man had a hand?', True],
  [348, 'The hand of a man moved a wheel. A man had a hand?', True],
  [349, 'The hand of a man moved a wheel. A man had a wheel?', None],

  # -- complex of-chains in events --

  [350, 'A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand of a man moved a wheel of a large wheelbarrow?', True],
  [351, 'A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand of an elephant moved a wheel of a large wheelbarrow?', None],
  [352, 'The blue hand of a man moved a wheel of the large wheelbarrow. A blue hand of a man moved a wheel of a large wheelbarrow?', True],
  [353, 'The blue hand of a man moved the wheel of the large wheelbarrow. The blue hand of a man moved the wheel of the large wheelbarrow?', True],
  [354, 'The blue hand of a man moved the wheel of the large wheelbarrow. The blue hand of a man moved the large wheelbarrow?', None],
  [355, 'A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel?', True],
  [356, 'A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheelbarrow?', None],
  [357, 'A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand moved a wheel?', True],
  [358, 'A blue hand of a man moved a wheel of a large wheelbarrow. A right hand moved a wheel?', None],
  [359, 'A blue hand of a man moved a wheel of a large wheelbarrow. A leg moved a wheel?', None],
  [360, 'A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel of a small wheelbarrow?', None],
  [361, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a hand?', True],
  [362, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a blue hand?', True],
  [363, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a red hand?', None],
  [364, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a wheel?', None],
  [365, 'A blue hand of a man moved a wheel of a large wheelbarrow. The wheelbarrow had a wheel?', True],
  [366, 'A blue hand of a man moved a wheel of a large wheelbarrow. A large wheelbarrow had the wheel?', True],
  [367, 'A blue hand of a man moved a wheel of a large wheelbarrow. The large wheelbarrow had a wheel?', True],
  [368, 'A blue hand of a man moved a wheel of a large wheelbarrow. The wheelbarrow had a hand?', None],
  [369, 'The blue hand of a man moved the wheel of the large wheelbarrow. Mary is a man?', None],
  [370, 'The blue hand of a man moved a wheel of the large wheelbarrow. Mary is a man?', None],

  [371, 'The hand of a man is nice. Mary is a man?', None],
  [372, 'A hand of a man moved a wheel. Mary is a man?', None],
  [373, 'The hand of a man moved a wheel. Mary is a man?', None],

  [374, 'John is not in a cave. John is in a cave?', False],
  [375, 'John does not eat a carrot. Mike eats carrots. Who eats carrots?', 'Mike'],
  [376, 'John does not eat a carrot. Mike eats carrots. Who does not eat carrots?', 'John'],
  [377, 'The big bear is strong. The bear is big?', True],
  [378, ' The white mouse is strong. The mouse is white?', True],
  [379, ' The big mouse is strong. The mouse is big?', True],

  [380, 'The big bear is strong. The bear is strong?', True],
  [381, 'The big bear is strong. The big bear is strong?', True],
  [382, 'The big bear is strong. The big bear is white?', None],

# == SETS AND COUNTING ==

  # -- basic numeric have --

  [383, 'John has three cars. John has three cars?', True],
  [384, 'If John has three cars, John has three cars?', True],
  [385, 'John has three nice cars. John has three nice cars?', True],

  # -- generic numeric have --

  [386, 'Animals have two legs. Animals have two legs?', True],
  [387, 'Animals have two legs. Animals have three legs?', False],
  [388, 'Animals have two nice legs. Animals have two nice legs?', True],
  [389, 'Animals have two nice legs. Animals have two long legs?', None],
  [390, 'An animal had two legs. The animal had two legs?', True],
  [391, 'An animal had two legs. The animal had three legs?', False],
  [392, 'An animal had two nice legs. The animal had two nice legs?', True],
  [393, 'An animal had two nice legs. The animal had two long legs?', None],

  # -- numeric have with relative clause --

  [394, 'John has three cars which are nice. John has three nice cars?', True],
  [395, 'John has three nice cars. John has three nice cars?', True],
  [396, 'John has three nice cars. John has three red cars?', None],
  [397, 'John has three nice big cars. John has three nice big cars?', True],
  [398, 'John has three nice big cars. John has three big nice cars?', True],

  [399, 'If John has three big nice cars, he is rich. John has three nice big cars. John is rich?', True],
  [400, 'If John has three big nice cars, he is rich. John has three nice big cars. Who is rich?', 'John'],
  [401, 'If John has three big nice cars, he is rich. John has three nice cars. John is rich?', None],

  [402, 'If a person has three big nice cars, he is rich. John has three nice big cars. John is rich?', True],

  # -- numeric have: existential inference --

  [403, 'John has three nice cars. John has a car?', True],
  [404, 'John has three nice cars. John has a nice car?', True],
  [405, 'An animal had two legs. The animal had legs?', True],
  [406, 'An animal had two legs. The animal had a leg?', True],
  [407, 'An animal had two strong legs. The animal had a strong leg?', True],
  [408, 'John has three nice cars. John has a red car?', None],

  # -- how many questions --

  [409, 'John has three nice cars. How many nice cars does John have?', ['Three', '3.']],

  [410, 'John has one car. John has cars?', True],

# == MEASURES ==

  # -- possessive measure assertions --

  [411, "Nile's length is 80 kilometers. The length of Nile is 80 kilometers?", True],
  [412, "Nile's length is 80 kilometers. The length of Nile is 90 kilometers?", False],

  [413, "Car's length is 80 kilometers. The length of the car is 80 kilometers?", True],
  [414, "Car's length is 80 kilometers. The length of the car is 90 kilometers?", False],
  [415, "The car's length is 80 kilometers. The length of the car is 80 kilometers?", True],
  [416, "The car's length is 80 kilometers. The length of the car is 90 kilometers?", False],

  [417, "The red car's length is 80 kilometers. The length of the blue car is 80 kilometers?", None],
  [418, "The red car's length is 80 kilometers. The length of the car is 90 kilometers?", False],
  [419, "Emajogi's length is 80 kilometers. Emajogi's length is 80 kilometers?", True],
  [420, "Emajogi's length is 80 kilometers. Emajogi's length is 90 kilometers?", False],

  # -- of-phrase measure assertions --

  [421, 'The length of Emajogi is 80 kilometers. Emajogi is 80 kilometers long?', True],
  [422, 'The length of Emajogi is 80 kilometers. Emajogi is 90 kilometers long?', False],
  [423, 'The nice Emajogi is 80 kilometers long. The nice Emajogi is 80 kilometers long?', True],
  [424, "The red car's length is 80 kilometers. What is the length of the red car?", ['80 kilometers', '80000 meters']],
  [425, "Emajogi's length is 80 kilometers. The length of Nile is 80 kilometers. Emajogi has the same length as Nile?", True],
  [426, 'The nice Emajogi is 80 kilometers long. What is 80 kilometers long?', ['Emajogi', 'The nice Emajogi.']],
  [427, 'The nice Emajogi is 80 kilometers long. The nice Emajogi is 90 kilometers long?', False],
  [428, 'The red straw is 10 meters long. The red straw is 10 meters long?', True],
  [429, 'The red straw is 10 meters long. The red straw is 20 meters long?', False],

  # -- has-measure assertions --

  [430, 'John has the length 2 meters. John is 2 meters long?', True],
  [431, 'John has the length 2 meters. John is 3 meters long?', False],
  [432, 'John has length of 2 meters. John is 2 meters long?', True],
  [433, 'John has length of 2 meters. John is 3 meters long?', False],
  [434, "John's length is 2 meters. John is 2 meters long?", True],

  # -- price assertions --

  [435, 'The price of the red car is 2 dollars. The price of the red car is 2 dollars?', True],
  [436, 'The price of the red car is 2 dollars. The price of the red car is 3 dollars?', False],
  [437, 'The price of the red car is 2 dollars. The price of the red car is 2 euros?', False],

  [438, 'The red car costs 2 dollars. The price of the red car is 2 dollars?', True],
  [439, 'The red car costs 2 dollars. The price of the red car is 3 dollars?', False],

  [440, 'The red car has a price of two dollars. The red car costs two dollars?', True],

  # -- has-price with word numbers --

  [441, 'The red car has the price two dollars. The red car costs two dollars?', True],
  [442, 'The red car has the price two dollars. The red car costs three dollars?', False],
  [443, 'The red car has the price two dollars. The blue car costs three dollars. The red car costs 3 dollars?', False],
  [444, 'The red car has the price two dollars. The blue car costs three dollars. The blue car costs 2 dollars?', False],
  [445, 'The red car has the price two dollars. The blue car costs three dollars. The car costs three dollars?', True],

  [446, 'The red car costs 2 dollars. What costs 2 dollars?', 'The red car'],

  # -- measure comparisons: below/above --

  [447, 'The price of the car is below 20 dollars. The car costs less than 20 dollars?', True],
  [448, 'The weight of the car is below 20 tons. The car weighs less than 20 tons?', True],
  [449, 'The price of the car is above 20 dollars. The car costs more than 20 dollars?', True],
  [450, 'The weight of the car is above 20 tons. The car weighs more than 20 tons?', True],
  [451, 'The price of the car is below 20 dollars. The price of the car is 25 dollars?', False],
  [452, 'The red car has the price two dollars. The blue car costs three dollars. The price of the red car equals the price of the blue car?', False],
  [453, 'The red car has the price two dollars. The blue car costs three dollars. The price of the red car equals the price of the red car?', True],

  [454, 'The red car has the price three dollars. The blue car costs three dollars. The price of the red car is the same as the price of the blue car?', True],

  # -- measure comparisons between entities --

  [455, 'The red car has the price three dollars. The blue car costs two dollars. The price of the red car is the same as the price of the blue car?', False],
  [456, 'The red car has the price three dollars. The blue car costs three dollars. The red car costs as much as the blue car?', True],
  [457, 'The red car has the price three dollars. The blue car costs two dollars. The red car costs as much as the blue car?', False],
  [458, 'The red car has the price three dollars. The blue car costs three dollars. The red car is as expensive as the blue car?', True],
  [459, 'The red car has the price three dollars. The blue car costs two dollars. The red car is as expensive as the blue car?', False],
  [460, 'The red car has the price three dollars. The blue car costs three dollars. The red car is as cheap as the blue car?', True],
  [461, 'The red car has the price three dollars. The blue car costs two dollars. The red car is as cheap as the blue car?', False],
  [462, 'The red car has the price three dollars. The blue car costs three dollars. The red car has the same price as the blue car?', True],
  [463, 'The red car has the price three dollars. The blue car costs two dollars. The red car has the same price as the blue car?', False],

  [464, 'The red car has the price two dollars. The blue car costs three dollars. The green car costs 2 dollars. The red car costs as much as the green car?', True],

  # -- length comparisons --

  [465, 'The length of the red car is three meters. The blue car is 2 meters long. The red car has the same length as the blue car?', False],
  [466, 'The length of the red car is three meters. The blue car is 2 meters long. The red car does not have the same length as the blue car?', True],
  [467, 'The length of the red car is three meters. The blue car is 3 meters long. The red car has the same length as the blue car?', True],
  [468, 'The length of the red car is three meters. The blue car is 3 meters long. The red car does not have the same length as the blue car?', False],

  [469, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is more than the length of the black car?""", False],
  [470, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is less than the length of the black car?""", True],
  [471, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is less than 2 meters?""", False],
  [472, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is over 2 meters?""", True],
  [473, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is more than 2 meters?""", True],
  [474, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is under 4 meters?""", True],

  [475, 'The length of the car is 3 meters. The bike has the same length as the car. The length of the bike is 3 meters?', True],

  # -- same-as measure equality --

  [476, 'The price of the car is 3 dollars. The bike has the same price as the car.  The price of the bike is 3 dollars?', True],

  [477, 'The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 3 dollars?', True],
  [478, 'The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 2 dollars?', False],
  [479, 'The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 3 drahms?', False],

  # -- as-much-as measure equality --

  [480, 'The price of the car is 3 dollars. The bike costs as much as the car. The bike costs 3 dollars?', True],
  [481, 'The price of the car is 3 dollars. The bike costs as much as the car. The price of the bike is less than 20 dollars?', True],
  [482, 'The price of the car is 3 dollars. The bike costs as much as the car. The price of the bike is more than 20 dollars?', False],
  [483, 'The price of the car is 3 dollars. The bike costs as much as the car. The bike costs less than 20 dollars?', True],
  [484, 'The price of the car is 3 dollars. The bike costs as much as the car. The bike costs more than 20 dollars?', False],

  [485, 'The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs less than 20 tons?', True],
  [486, 'The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs more than 2 tons?', True],
  [487, 'The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs more than 20 tons?', False],

  # -- what-questions on measures --

  [488, "Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What is 80 kilometers long?", 'Nile'],
  [489, "Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What has the length 20 kilometers?", 'Amazon'],

  [490, "Car's length is 80 kilometers. Bike's length is 10 kilometers. What is 80 kilometers long?", 'A car'],
  [491, "Car's length is 80 kilometers. Bike's length is 10 kilometers. What has the length 10 kilometers?", 'A bike'],
  [492, "The car's length is 80 kilometers. The bike's length is 10 kilometers. What is 80 kilometers long?", 'The car'],
  [493, "The car's length is 80 kilometers. The bike's length is 10 kilometers. What has the length 10 kilometers?", 'The bike'],

  [494, "Emajogi's length is 80 kilometers. What is 80 kilometers long?", 'Emajogi'],
  [495, "Emajogi's length is 80 kilometers. What is 200 kilometers long?", None],
  [496, 'The length of Nile is 10 meters. What has the length 10 meters?', 'Nile'],

  # -- what-is-N-long questions --

  [497, 'Nile is 10 meters long. What is 10 meters long?', 'Nile'],
  [498, 'Nile is 10 meters long. Emajogi is 20 meters long. The nice river is 100 meters long. What is 100 meters long?', 'The nice river'],
  [499, 'The red straw is 10 meters long. The blue straw is 5 meters long. What is 5 meters long?', 'The blue straw'],
  [500, 'The red straw is 10 meters long. The blue straw is 5 meters long. What is 10 meters long?', 'The red straw'],

  [501, 'The red car has the price two dollars. The blue car costs three dollars. What costs 3 dollars?', 'The blue car'],
  [502, 'The red car has the price two dollars. The blue car costs three dollars. What has the price 2 dollars?', 'The red car'],
  [503, 'The red car has the price two dollars. The blue car costs three dollars. What has the price 3 dollars?', 'The blue car'],

  [504, 'The bicycle repaired by Mike was expensive. Mike repaired the bicycle?', True],
  [505, 'The bicycle repaired by Mike was expensive. The bicycle was expensive?', True],
  [506, 'The bicycle repaired by Mike was expensive. The bicycle was cheap?', False],

# == QUANTIFIERS: UNIVERSAL & EXISTENTIAL ==

  # -- all implies bare plural --

  [507, 'All elephants are animals. Elephants are animals?', True],
  [508, 'All elephants are animals. Some elephant is an animal?', True],
  [509, 'All elephants are animals. All elephants are animals?', 'True'],
  [510, 'All elephants are animals. John is an animal?', None],
  [511, 'All elephants are animals. Elephants are not animals?', False],
  [512, 'All elephants are animals. Some elephants are not animals?', False],
  [513, 'All elephants are animals. All elephants are not animals?', False],

  # -- some: existential --

  [514, 'Some elephants are animals. Elephants are animals?', None],
  [515, 'Some elephants are animals. Some elephant is an animal?', True],
  [516, 'Some elephants are animals. All elephants are animals?', None],
  [517, 'Some elephants are animals. John is an animal?', None],
  [518, 'Some elephants are animals. Elephants are not animals?', False],
  [519, 'Some elephants are animals. Some elephants are not animals?', None],
  [520, 'Some elephants are animals. All elephants are not animals?', False],
  [521, 'Some elephants are not animals. All elephants are animals?', False],

  # -- all-not vs not-all --


  [522, 'No elephant is an animal. No elephant is an animal?', True],
  [523, 'No elephant is an animal. Some elephant is an animal?', False],

  # -- all in object position --

  [524, 'John likes all boxers. Mike is a boxer. John likes Mike?', True],
  [525, 'Bears eat all boxers. Mike is a boxer. Greg is a bear. Greg eats Mike?', True],
  [526, 'Bears eat most boxers. Mike is a boxer. Greg is a bear. Bears eats Mike?', 'Probably true.'],
  [527, 'Bears eat most boxers. Mike is a boxer. Greg is a bear. Bears eats Greg?', None],
  [528, 'Bears eat all boxers. Mike is a boxer. Bears eat boxers?', True],
  [529, 'Bears eat some boxers. Mike is a boxer. Bears eat Mike?', None],
  [530, 'John likes some boxers. Mike is a boxer. John likes Mike?', None],

  [531, 'Elephants are animals. Some elephant is an animal?', True],
  [532, 'Elephants are animals. All elephants are animals?', True],
  [533, 'Elephants are animals. John is an animal?', None],
  [534, 'Elephants are animals. Elephants are not animals?', False],
  [535, 'Elephants are animals. Some elephants are not animals?', False],
  [536, 'Elephants are animals. All elephants are not animals?', False],

# == QUANTIFIERS: PROPORTIONAL & NUMERIC ==

  # -- distinct indefinites with quantifiers --

  [537, 'The red square has a nail. A blue square has a hole. A square has a nail?', True],
  [538, 'The red square has a nail. A blue square has a hole. A square has a hole?', True],
  [539, 'The red square has a nail. A blue square has a hole. A square has a dot?', None],
  [540, 'The red square has a nail. A blue square has a hole. A red square has a nail?', True],
  [541, 'The red square has a nail. A blue square has a hole. A blue square has a hole?', True],
  [542, 'The red square has a nail. A blue square has a hole. A red square has a hole?', None],

  [543, 'The red square is nice. A blue square is cool. Some square is cool?', True],
  [544, 'The red square is nice. A blue square is cool. There is a nice square?', True],
  [545, 'The red square is nice. A blue square is cool. A square is empty?', None],

  [546, 'Most bears are big. John is a bear. John is big?', 'Likely true.'],

# == COMPARATIVES & EQUALITY ==

  # -- basic comparatives --

  [547, 'John is nicer than Mike. Mike is nicer than Eve. Who is nicer than Eve?', ['John and Mike.', 'John.', 'Mike.']],
  [548, 'John is nicer than Mike. Mike is nicer than Eve. Who is nicer than John?', None],
  [549, 'The red car is faster than the blue car. Is the blue car faster than the red car?', False],
  [550, 'The red car is faster than the blue car. Is the green car faster than the red car?', None],

  # -- equality comparisons --

  [551, 'John is as tall as Bill. Is John taller than Bill?', False],
  [552, "John is as tall as Bill. Is John's height equal to Bill's?", True],

  # -- which-questions on comparatives --

  [553, 'The mountain is higher than the hill. Is the hill higher than the mountain?', False],
  [554, "This book is more interesting than that one. Is 'that one' more interesting?", False],

# == COORDINATION (NP, VP, CLAUSAL) ==

  # -- NP coordination with lists --

  [555, 'Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a toy?', True],
  [556, 'Elephants, foxes and rabbits are nice animals and good toys. John is a fox. John is a good toy?', True],
  [557, 'Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal?', True],
  [558, 'Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal and a toy?', True],
  [559, 'Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal or a toy?', True],

  [560, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a bird?', False],
  [561, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is not a bird?', True],
  [562, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a small fish?', False],
  [563, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a fish?', None],

  [564, 'Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a red toy?', None],

  # -- either-or coordination --

  [565, 'Elephants and sparrows are either animals or birds. John is a sparrow. John is a bird. John is an animal?', False],
  [566, 'Elephants and sparrows are either animals or birds. John is a sparrow. Sparrows are birds. John is not an animal?', True],
  [567, 'Elephants and sparrows are animals or birds. John is a sparrow. John is a bird. John is an animal or a bird?', True],
  [568, 'Elephants and sparrows are animals or birds. John is a sparrow. John is a bird. John is an elephant?', None],
  [569, 'Elephants or sparrows are animals. John is an elephant. Sparrows are not animals. John is an animal?', True],

  # -- class independence --

  [570, 'Elephants are animals. Birds are animals?', None],
  [571, 'Elephants are animals. Birds are nice animals?', None],

  [572, 'John saw the blue head of the red elephant. John saw the blue head of the red elephant?', True],
  [573, 'John saw the blue head of the red elephant. John saw the red head of the blue elephant?', None],

# == LISTS AND CONJUNCTIONS ==

  # -- conjunction of class properties --

  [574, 'Cars are nice. Cars have brakes. Cars are nice and have brakes?', True],
  [575, 'Cars are nice. Cars are nice and have brakes?', None],
  [576, 'Cars have brakes. Cars are nice and have brakes?', None],
  [577, 'Cars are nice and cool and have brakes. Cars are nice and cool and have brakes?', True],
  [578, 'Cars are nice and cool and have brakes. Cars have brakes and are nice and cool?', True],
  [579, 'Cars are cool and have brakes. Cars are nice and cool and have brakes?', None],
  [580, 'Cars are nice and cool. Cars have brakes and are nice and cool?', None],
  [581, 'Cars have fenders. Cars have brakes. Cars have brakes and fenders?', True],
  [582, 'Cars have fenders. Cars have brakes and fenders?', None],
  [583, 'Cars have brakes. Cars have brakes and fenders?', None],

  # -- NP conjunction as subject --

  [584, 'John and Mary saw the movie. Did Mary see the movie?', True],
  [585, 'John and Mary saw the movie. Did Mary see a play?', None],
  [586, 'John and Mary saw the movie. Who saw the movie?', 'John and Mary.'],

  # -- conjoined adjectives --

  [587, 'A tall and quiet man entered. A man entered?', True],
  [588, 'A tall and quiet man entered. A woman entered?', None],
  [589, 'A tall and quiet man entered. The man was tall?', True],
  [590, 'A tall and quiet man entered. The man was quiet?', True],
  [591, 'A tall and quiet man entered. The man was short?', False],

  [592, 'A red and blue flag waved. The flag was red?', True],
  [593, 'A red and blue flag waved. The flag was blue?', True],

  # -- conjoined objects --

  [594, 'John bought a red car and a blue bicycle. John bought a car?', True],
  [595, 'John bought a red car and a blue bicycle. John bought a bicycle?', True],
  [596, 'John bought a red car and a blue bicycle. Did John buy a truck?', None],
  [597, 'John bought a red car and a blue bicycle. The car was red?', True],
  [598, 'John bought a red car and a blue bicycle. The bicycle was blue?', True],
  [599, 'John bought a red car and a blue bicycle. The car was blue?', False],

  # -- VP conjunction --

  [600, 'The cat sat on the mat and purred. Did the cat purr?', True],
  [601, 'The cat sat on the mat and purred. Did the cat bark?', None],

  # -- conjoined VPs with different objects --

  [602, 'John ate an apple and drank some water. What did John drink?', ['Water.', 'Some water.']],
  [603, 'John ate an apple and drank some water. Did John eat a banana?', None],
  [604, 'The students studied hard and passed the exam. Did the students pass the exam?', True],
  [605, 'The students studied hard and passed the exam. Did the students fail the exam?', False],

  # -- conjoined verbs, shared object --

  [606, 'Mary washed and dried the cup. Mary washed the cup?', True],
  [607, 'Mary washed and dried the cup. Mary dried the cup?', True],
  [608, 'Mary washed and dried the cup. Did Mary break the cup?', None],

  [609, 'Tom opened the door and the window. Tom opened the door?', True],
  [610, 'Tom opened the door and the window. Tom opened the window?', True],
  [611, 'Tom opened the door and the window. Tom did not open the door?', False],

  [612, 'John bought a red car and a blue bicycle. What did John buy?', 'A red car and a blue bicycle'],
  [613, 'Tom opened the door and the window. What did Tom open?', 'The door and the window'],
  [614, 'Mary washed and dried the cup. Did Mary iron the cup?', None],

  # -- conjunction with can --

  [615, 'John and Eve can swim. Mark and John are animals. Who can swim and is an animal?', 'John'],
  [616, 'John and Eve can swim. Mark and John are animals. Who is an animal and can swim?', 'John'],
  [617, 'John and Eve can swim. Mark is an animal. Who can swim and is an animal?', None],

  # -- either-or --

  [618, 'Either John or Bill went to the store. Did someone go to the store?', True],
  [619, 'Either John or Bill went to the store. Did Mary go to the store?', None],

  # -- class defaults --

  [620, 'Cars are nice. Cars are nice?', True],

  # -- subclass exceptions --

  [621, 'Red cars are not nice. Cars are nice. Cars are nice?', True],
  [622, 'Red cars are not nice. Cars are nice. Red cars are nice?', False],
  [623, 'Red cars are not nice. Cars are nice. Blue cars are nice?', True],

  [624, 'Penguins happily live in water. Penguins happily live in water?', True],
  [625, 'Penguins happily live in cold water. Penguins happily live in cold water?', True],

# == INTERNAL MODIFICATION ==


  # -- basic appositive --

  [626, 'John, a doctor, arrived. John is a doctor?', True],
  [627, 'John, a doctor, arrived. John is a nurse?', None],
  [628, 'Mary, a pilot, smiled. Who is a pilot?', 'Mary.'],
  [629, 'Paul, a carpenter, carried a box. Paul carried a box?', True],
  [630, 'Paul, a carpenter, carried a box. Paul is a plumber?', None],

  [631, 'The manager, Anna, called Eve. Anna is the manager?', True],

  [632, 'John, my neighbor, owns a bicycle. John owns a bicycle?', True],
  [633, 'My neighbor, John, owns a bicycle. Who is my neighbor?', 'John.'],
  [634, 'Dr. Smith, a surgeon, entered the room. Dr. Smith is a surgeon?', True],
  [635, 'Dr. Smith, a surgeon, entered the room. Dr. Smith is a dentist?', None],

  [636, 'Tom, a friend of Mary, laughed. Tom is a friend of Mary?', True],
  [637, 'Tom, a friend of Mary, laughed. Mary is a friend of Tom?', None],
  [638, 'Tom, a friend of Mary, laughed. Tom is a friend of Eve?', None],

  [639, 'Sara, the sister of Mike, left. Sara is the sister of Mike?', True],
  [640, 'Sara, the sister of Mike, left. Sara is the brother of Mike?', False],

  # -- noun-noun compounds --

  [641, 'A school bus arrived. A bus arrived?', True],
  [642, 'A school bus arrived. A truck arrived?', None],
  [643, 'A chocolate cake fell. A cake fell?', True],
  [644, 'A chocolate cake fell. A pie fell?', None],
  [645, 'A stone wall collapsed. A wall collapsed?', True],
  [646, 'A kitchen door was open. A door was open?', True],

  # -- adjective from noun modifier --

  [647, 'A village road was narrow. A road was narrow?', True],
  [648, 'A coffee cup broke. A cup broke?', True],
  [649, 'A coffee cup broke. A plate broke?', None],
  [650, 'A garden wall was high. Some wall was high?', True],
  [651, 'A garden wall was high. A wall was low?', None],

  # -- present participial modifier --

  [652, 'The man carrying a bag waved. The man carried a bag?', True],
  [653, 'The man carrying a bag waved. The man carried a box?', None],

  # -- holding as participial --

  [654, 'The woman holding a lamp sang. The woman held a lamp?', True],
  [655, 'The child wearing a hat ran. The child wore a hat?', True],
  [656, 'The child wearing a hat ran. The child wore a coat?', None],

  # -- containing as participial --

  [657, 'The box containing apples fell. The box contained apples?', True],
  [658, 'The box containing apples fell. The box contained oranges?', None],

  # -- standing as participial --

  [659, 'The man standing by the door coughed. The man stood by the door?', True],
  [660, 'The man standing by the door coughed. The man stood by the window?', None],

  # -- parked as participial --

  [661, 'The car parked behind the house was blue. The car was behind the house?', True],
  [662, 'The car parked behind the house was blue. The car was in front of the house?', False],
  [663, 'The children playing in the garden laughed. The children were in the garden?', True],
  [664, 'The cup filled with water fell. The cup contained water?', True],
  [665, 'The road leading to the village was narrow. The road led to the village?', True],
  [666, 'The road leading to the village was narrow. The road was wide?', False],
  [667, 'The tree growing near the river was tall. The tree grew near the river?', True],

  # -- participial with modified object --

  [668, 'The man carrying a red bag waved. The bag was red?', True],
  [669, 'The man carrying a red bag waved. The bag was blue?', False],
  [670, 'The woman holding a heavy lamp sang. The lamp was heavy?', True],
  [671, 'The woman holding a heavy lamp sang. The lamp was light?', False],
  [672, 'The child wearing a small hat ran. The hat was small?', True],
  [673, 'The letter written by Mary was long. Mary wrote a long letter?', True],
  [674, 'The letter written by Mary was long. The letter was short?', False],
  [675, 'The cake baked by John was sweet. John baked a sweet cake?', True],
  [676, 'The dog chased by the boy was black. The boy chased a black dog?', True],
  [677, 'The dog chased by the boy was black. The dog was white?', False],

  # -- past participial modifier --

  [678, 'The letter written by Mary arrived. Mary wrote the letter?', True],
  [679, 'The cake baked by John was sweet. John baked the cake?', True],
  [680, 'The cake baked by John was sweet. The cake was bitter?', False],
  [681, 'The song sung by Eve was sad. Eve sang the song?', True],

  # -- passive participial --

  [682, 'The dog chased by the boy escaped. The boy chased the dog?', True],
  [683, 'The dog chased by the boy escaped. Did the dog catch the boy?', None],
  [684, 'The woman admired by John smiled. John admired the woman?', True],

  [685, 'The doctor who treated Mary called John. The doctor treated Mary?', True],
  [686, 'The doctor who treated Mary called John. The doctor called John?', True],
  [687, 'The doctor who treated Mary called John. Did the doctor treat John?', None],

  [688, 'The painter who lived in Rome sold a picture. The painter lived in Rome?', True],
  [689, 'The painter who lived in Rome sold a picture. The painter sold a picture?', True],
  [690, 'The painter who lived in Rome sold a picture. Did the painter live in Paris?', None],

  [691, "John's friend from Paris bought a camera. John had a friend?", True],
  [692, "John's friend from Paris bought a camera. The friend was from Paris?", True],
  [693, "John's friend from Paris bought a camera. Was the friend from London?", None],

  [694, "Mary's brother carrying a box entered. Mary had a brother?", True],
  [695, "Mary's brother carrying a box entered. The brother carried a box?", True],
  [696, "Mary's brother carrying a box entered. Did the brother carry a bag?", None],

  [697, 'The student carrying the books greeted the teacher. The student carried the books?', True],
  [698, 'The student carrying the books greeted the teacher. The student greeted the teacher?', True],
  [699, 'The student carrying the books greeted the teacher. Did the student greet the principal?', None],

  [700, 'The letter was written in June. Was the letter written?', True],
  [701, 'Bears ate berries in a forest. Bears did not eat berries in a forest?', False],
  [702, 'Bears ate berries in a forest. Bears did not eat berries in a field?', None],

# == RELATIVE CLAUSES ==

  # -- who-clauses in rules --

  [703, 'Big bears who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', True],
  [704, 'Big bears who have a trunk have a tail. John is a big bear. John has a nose. John has a tail?', None],
  [705, 'Big bears who have a trunk have a tail. John is a bear. John has a trunk. John has a tail?', None],

  [706, 'Big bears who are nice and have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', None],
  [707, 'Big bears who are nice and have a trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', True],
  [708, 'Big bears who are nice and who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', None],
  [709, 'Big bears who are nice and who have a trunk have a tail. John is a big bear. John is nice. John has a tail?', None],
  [710, 'Big bears who are nice and who have a trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', True],

  [711, 'Bears who are nice and have a long trunk have a tail. John is a nice big bear. John has a long trunk. John has a tail?', True],
  [712, 'Bears who are nice and have a long trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', None],
  [713, 'Bears who have a trunk are nice. John is a bear. John has a trunk. John is nice?', True],
  [714, 'Bears who have a trunk are nice. John is a bear. John has a nose. John is nice?', None],

  [715, 'Bears who are nice and eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?', True],
  [716, 'Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?', True],
  [717, 'Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats fish. John has a tail?', None],

  # -- simple who-clauses --

  [718, 'Bears who are big are strong. John is a big nice bear. John is strong?', True],
  [719, 'Bears who are big are strong. John is a bear. John is strong?', None],
  [720, 'Bears who have tails are strong. John is a big nice bear. John has a tail. John is strong?', True],
  [721, 'Bears who have tails are strong. John is a big nice bear.  John is strong?', None],
  [722, 'Bears who eat fish are strong. John eats fish. John is a bear. John is strong?', True],
  [723, 'Bears who eat fish are strong. John is a bear. John is strong?', None],
  [724, 'Bears who eat fish are strong. John eats carrots. John is a bear. John is strong?', None],
  [725, 'Nice bears who have tails are strong. John is a nice bear. John has a tail. John is strong?', True],
  [726, 'Nice bears who have tails are strong. John is a bear. John has a tail. John is strong?', None],
  [727, 'Nice bears who have tails are strong. John is a nice bear. John has a head. John is strong?', None],

  # -- who-clauses with pre-modifier --

  [728, 'Nice bears who are big are strong. John is a big nice bear. John is strong?', True],
  [729, 'Nice bears who are big are strong. John is a nice bear. John is strong?', None],
  [730, 'Nice bears who eat fish are strong. John is a nice bear. John eats fish. John is strong?', True],

  [731, 'Nice bears who eat big fish are strong. John is a nice bear. John eats big fish. John is strong?', True],
  [732, 'Nice bears who eat big fish are strong. John is a nice bear. John eats big carrots. John is strong?', None],
  [733, 'Nice bears who eat big fish are strong. John is a nice bear. John eats fish. John is strong?', None],

  # -- the-definite with who-clause --

  [734, 'The bear who is big is strong. The bear is strong?', True],
  [735, 'The bear who is big is strong. The big bear is strong?', True],
  [736, 'The bear who is big is strong. The big bear is white?', None],
  [737, 'The bear who is big is strong. Who is strong?', ['The big bear', 'The bear who is big.', 'The bear.']],

  [738, 'The bear who is big eats fish. The bear who is big eats fish?', True],
  [739, 'The bear who is white eats fish. The bear who is white eats fish?', True],

  [740, 'The bear who was white ate a fish. The bear who was white ate a fish?', True],
  [741, 'The bear who was white ate a fish. The bear ate a fish?', True],
  [742, 'The bear who was white ate a fish. The white bear ate a fish?', True],

  [743, 'Bears who were nice ate. Nice bears ate?', True],
  [744, 'The bear who was nice ate. The bear ate?', True],

  [745, 'Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat fish?', True],
  [746, 'Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat tables?', None],
  [747, 'Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat fish who are strong?', [True, 'Likely true']],
  [748, 'Bears who are nice eat fish who are strong. John is a nice bear. Nice bears eat strong fish?', [True, 'Likely true']],

  # -- past-tense who-clauses --

  [749, 'The bear who was nice ate the fish who was strong. The bear who was nice ate the fish who was strong?', True],
  [750, 'The bear who was nice ate the fish who was strong. The nice bear ate the strong fish?', True],
  [751, 'The bear who was nice ate the fish who was strong. The bear who was nice ate the fish who was white?', None],

  [752, 'The bear who was nice and white ate the fish who was big. The nice bear ate the big fish?', True],

  # -- conjoined who-clauses --

  [753, 'The bear who was white and ate a fish was cool. The white bear who ate a fish was cool?', True],
  [754, 'The bear who was white and ate a fish was cool. The bear who ate a fish was cool?', True],
  [755, 'The bear who was white and ate a fish was cool. The white bear who ate a fish was strong?', None],
  [756, 'The bear who was white and ate a fish was cool. The black bear who ate a fish was cool?', None],

  [757, 'The bear who was white and ate a big fish was cool. The white bear who ate a big fish was cool? ', True],
  [758, 'The bear who was white and ate a big fish was cool. The white bear who ate a fish was cool? ', True],
  [759, 'The bear who was white and ate a big fish was cool. The white bear who ate a strong fish was cool? ', None],

  [760, 'The nice bear who was white and ate a big fish was cool. The white nice bear who ate a big fish was cool? ', True],
  [761, 'The nice bear who was white and ate a big fish also ate berries. The white nice bear who ate a big fish also ate berries? ', True],
  [762, 'The nice bear who was white and ate a big fish also ate blue berries. The white nice bear who ate a big fish also ate blue berries? ', True],
  [763, 'The nice bear who was white and ate a big fish also ate blue berries. The white nice bear who ate a big fish also ate berries? ', True],
  [764, 'The nice bear who was white and ate a big fish also ate blue berries. The bear ate berries? ', True],
  [765, 'The nice bear who was white and ate a big fish also ate blue berries. The bear ate bread? ', None],

  [766, 'The bear who ate a big fish ate blue berries. The bear who ate a fish also ate blue berries?', True],
  [767, 'The bear who ate a big fish ate blue berries. The bear who ate a fish ate big berries?', None],
  [768, 'The bear who ate a big fish ate blue berries. John is big?', None],
  [769, 'The bear who ate a big fish ate blue berries. John is blue?', None],
  [770, 'The bear who ate a big fish ate blue berries. John is a fish?', None],

  # -- conjoined verbs in who-clause --

  [771, 'The woman who sang and danced smiled. The woman sang?', True],
  [772, 'The woman who sang and danced smiled. The woman danced?', True],
  [773, 'The woman who sang and danced smiled. The woman did not sing?', False],

  [774, 'The boy with a red hat and a blue coat ran. The boy had a red hat?', True],
  [775, 'The boy with a red hat and a blue coat ran. The boy had a blue coat?', True],

  # -- who-clause on object --

  [776, 'Bears eat fish who are strong. John is a bear. John eats strong fish?', True],
  [777, 'Bears eat fish who are strong. John is a fox. John eats strong fish?', None],
  [778, 'Bears eat fish who are strong. John is a bear. John eats red fish?', None],

  [779, 'Bears eat red fish who are strong. John is a bear. John eats red strong fish?', True],
  [780, 'Bears eat red fish who are strong. John is a bear. John eats yellow strong fish?', None],
  [781, 'Bears eat red fish who are strong. John is a bear. John eats yellow fish?', None],

  # -- subject and object who-clauses --

  [782, 'Bears who are nice eat fish who are strong. John is a nice bear. John eats strong fish?', True],
  [783, 'Bears who are nice eat fish who are strong. John is a bear. John eats strong fish?', None],
  [784, 'Bears who are nice eat fish who are strong. John is a nice bear. John eats yellow fish?', None],

  [785, 'Bears who are nice and white eat fish who are strong and red. John is a nice white bear. John eats red strong fish?', True],
  [786, 'Bears who are nice and white eat fish who are strong and red. John is a nice bear. John eats red strong fish?', None],
  [787, 'Bears who are nice and white eat fish who are strong and red. John is a nice white bear. John eats yellow strong fish?', None],

  # -- which-clauses on objects --

  [788, 'A man liked a car which a woman bought. The car was red. The man liked the car which a woman bought?', True],
  [789, 'A man liked a car which a woman bought. The car was red. The man liked the red car which a woman bought?', True],
  [790, 'A man liked a car which a woman bought. The car was red. The man liked a car which a boy bought?', None],
  [791, 'A man liked a car which a woman bought. The car was red. A man liked a red car which a woman bought?', True],
  [792, 'A man liked a car which a woman bought. The car was red. The man did not like the red car which the woman bought?', False],
  [793, 'A man liked a car which a woman bought. The car was red. The man did not like the red car which a woman bought?', False],

  # -- which-clause with pronoun --

  [794, 'A man liked a car which he bought. The car was red. The man bought the red car?', True],
  [795, 'A man liked a car which he bought. The car was red. A man bought a red car?', True],

  # -- which-clause adding properties --

  [796, 'John has a red car which is nice and big. The nice car is big and red?', True],
  [797, 'Bears ate berries in a forest which was bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  [798, 'Bears ate berries in a forest which was seen by Mary. Bears ate berries in the forest seen by Mary?', True],
  [799, 'Bears ate berries in a forest which was bought by Mike. Bears ate berries in the forest bought by Mike?', True],
  [800, 'Bears ate berries in a forest which was bought by Mary. Bears ate berries in the forest bought by John?', None],
  [801, 'John lives in a red car bought by Mary. Mary bought the car?', True],

  [802, 'Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest which was bought by Mary?', True],
  [803, 'Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest which was bought by John?', None],
  [804, 'Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest bought by Mary?', True],

  [805, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by Mary?', True],
  [806, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by John?', None],
  [807, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  [808, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by John?', None],

  [809, 'A man had a car which a woman bought. The car was red. Who had a red car?', ['The man', 'The man and the woman.', 'The woman.']],

  # -- which-clause on location --

  [810, 'Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest which was bought by her?', True],
  [811, 'Bears ate nice berries in a big forest which was seen by Mary. Bears ate berries in the forest which was seen by her?', True],
  [812, 'Bears ate nice berries in a big forest which was bought by Mike. Bears ate berries in the forest which was bought by him?', True],
  [813, 'Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest which was bought by a man?', None],
  [814, 'Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest?', True],

  [815, 'Bears ate berries in the forest which was bought by Mary. The forest was bought by Mary?', True],

  # -- which-clause on location object --

  [816, 'John lives in a car which is red. The car is red?', True],
  [817, 'John lives in a car which is red. The car is nice?', None],
  [818, 'John lives in a car which is red. John lives in a red car?', True],
  [819, 'John lives in a car which is red. John lives in a nice car?', None],

  [820, 'John lives in a car which is red and was bought by Mary. The nice car was bought by Mary?', None],

  [821, 'John has a car which is nice and red. The car is red and nice?', True],
  [822, 'John has a car which is nice and red. The red car is nice?', True],
  [823, 'John has a car which is nice and red. The big car is nice?', None],

  # -- named entities in which-clauses --

  [824, 'John had a car which Eve bought. John had a car which Eve bought?', True],
  [825, 'John had a car which Eve bought. John had a car which Eve saw?', None],
  [826, 'John had a car which Eve bought. John had a car which Mike bought?', None],
  [827, 'John had a car which Mike bought. John had a car Mike bought?', True],
  [828, 'John had a car which Eve bought. John had a car Eve saw?', None],
  [829, 'John had a car which Eve bought. John had a car Mike bought?', None],
  [830, 'John had a car Mike bought. John had a car Mike bought?', True],
  [831, 'John had a car Eve bought. John had a car Mike bought?', None],
  [832, 'John had a car Eve bought. John had a car Eve saw?', None],
  [833, 'John had a car Eve bought. John had a car which Eve bought?', True],
  [834, 'John had a car Eve bought. John had a car which Eve saw?', None],
  [835, 'John had a car Eve bought. John had a car which Mike bought?', None],
  [836, 'John had a car Eve bought. Eve bought a car?', True],

  [837, 'John had a car Eve liked. Eve had a car?', None],

  [838, 'John had a red car Eve bought. John had a car which Eve bought?', True],
  [839, 'John had a red car which Mike bought. John had a car Mike bought?', True],
  [840, 'John had a red car Eve bought. John had a black car which Eve bought?', None],
  [841, 'John had a red car which Eve bought. John had a black car Eve bought?', None],

  [842, 'John had a car Eve bought. John had a car which Eve did not buy?', None],
  [843, 'John had a car which Mike did not buy. John had a car Mike did not buy?', True],
  [844, 'John did not have a red car which Eve bought. John did not have a red car which Eve bought?', True],

  # -- drove + which-clause --

  [845, 'John drove a car which Eve bought. John drove a car which Eve bought?', True],
  [846, 'John drove a car which Eve bought. John drove a car which Eve saw?', None],
  [847, 'John drove a car which Eve bought. John drove a car which Mike bought?', None],
  [848, 'John drove a car which Eve bought. John drove a car Eve bought?', True],
  [849, 'John drove a car which Eve bought. John drove a car Eve saw?', None],
  [850, 'John drove a car which Eve bought. John drove a car Mike bought?', None],
  [851, 'John drove a car Mike bought. John drove a car Mike bought?', True],
  [852, 'John drove a car Eve bought. John drove a car Mike bought?', None],
  [853, 'John drove a car Eve bought. John drove a car Eve saw?', None],
  [854, 'John drove a car Mike bought. John drove a car which Mike bought?', True],
  [855, 'John drove a car Eve bought. John drove a car which Eve saw?', None],
  [856, 'John drove a car Eve bought. John drove a car which Mike bought?', None],
  [857, 'John drove a car Eve bought. Eve drove a car?', None],
  [858, 'John drove a car Eve bought. John drove a car?', True],

  [859, 'John drove a red car Mike bought. John drove a car which Mike bought?', True],
  [860, 'John drove a red car which Eve bought. John drove a car Eve bought?', True],
  [861, 'John drove a red car Eve bought. John drove a black car which Eve bought?', None],
  [862, 'John drove a red car which Eve bought. John drove a black car Eve bought?', None],

  [863, 'John drove a car Eve bought. John drove a car which Eve did not buy?', None],
  [864, 'John drove a car which Mike did not buy. John drove a car Mike did not buy?', True],

  # -- whom-clauses --

  [865, 'John is a man whom Eve liked. John is a man whom Eve liked?', True],
  [866, 'John is a man whom Eve liked. John is a man whom Eve saw?', None],
  [867, 'John is a man whom Eve liked. John is a man whom Mike liked?', None],
  [868, 'John is a man whom Eve liked. John is a man Eve liked?', True],
  [869, 'John is a man whom Eve liked. John is a man Eve saw?', None],
  [870, 'John is a man whom Eve liked. John is a man Mike liked?', None],

  # -- reduced whom-clauses --

  [871, 'John is a man Eve liked. John is a man Eve liked?', True],
  [872, 'John is a man Eve liked. John is a man Mike liked?', None],
  [873, 'John is a man Eve liked. John is a man Eve saw?', None],
  [874, 'John is a man Eve liked. John is a man whom Eve liked?', True],
  [875, 'John is a man Eve liked. John is a man whom Eve saw?', None],
  [876, 'John is a man Eve liked. John is a man whom Mike liked?', None],

  [877, 'John is a strong man Eve liked. John is a strong man whom Eve liked?', True],
  [878, 'John is a strong man whom Eve liked. John is a strong man Eve liked?', True],
  [879, 'John is a strong man Eve liked. John saw a strong man whom Eve liked?', None],
  [880, 'John is a strong man whom Eve liked. John saw a strong man Eve liked?', None],

  [881, 'John is a man Eve liked. John is a man whom Eve did not like?', False],
  [882, 'John is a man whom Eve did not like. John is a man Eve did not like?', True],

  [883, 'John is not a man whom Eve liked. John is not a man whom Eve liked?', True],
  [884, 'John is a man Eve liked. John is a man?', True],
  [885, 'John is a man Eve liked. Eve liked John?', True],
  [886, 'John is a man Mary liked. Mary liked a man?', True],
  [887, 'John is a man Mary liked. Mary liked the man?', True],

  # -- that-clauses --

  [888, 'The book that Mary bought is on the table. Who bought the book?', 'Mary.'],
  [889, 'The book that Mary bought is on the table. Did John buy the book?', None],
  [890, 'The car which John drove was red. What color was the car?', 'Red.'],
  [891, 'The car which John drove was red. Was the car blue?', False],
  [892, 'The student who passed the test studied a lot. Did the student study?', True],
  [893, 'The student who passed the test studied a lot. Did the student fail the test?', False],

  [894, 'The man who laughed and who waved left. The man laughed?', True],
  [895, 'The man who laughed and who waved left. The man waved?', True],
  [896, 'The man who laughed and who waved left. Did the man cry?', None],

  # -- who-clause queries --

  [897, 'The man who saw John is tall. Who saw John?', 'The man.'],
  [898, 'The man who saw John is tall. Did John see the man?', None],
  [899, 'The man whom John saw is tall. Who did John see?', ['The man.', 'The tall man.']],
  [900, 'The man whom John saw is tall. Is the man short?', False],

  # -- have with relative clauses --

  [901, 'A man had a car which a nice woman bought. The car was red. Who bought the red car?', 'The nice woman'],
  [902, 'A man had a car which a nice woman bought. The car was red. Who bought a car?', 'The nice woman'],
  [903, 'A man had a car which a nice woman bought. The car was red. Who was nice?', 'The woman'],
  [904, 'A man had a car which a nice woman bought. The car was red. Who was nice and bought a car?', ['The woman', 'The nice woman.']],
  [905, 'A man had a car which a nice woman bought. The car was red. Who bought the black car?', None],

  [906, 'A big bear was strong. The bear was nice. Who was nice and strong?', ['The big bear.', 'The bear.']],

  [907, 'A big bear was strong. The small bear was nice. Who was nice and strong?', None],
  [908, 'A big bear was strong. The small bear was nice. Who was nice?', 'The small bear.'],
  [909, 'A big bear was strong. The small bear was nice. Who was strong?', 'The big bear.'],

  [910, 'A bear was strong. The bear was nice. Who was nice and strong?', 'The bear.'],
  [911, 'The big bear is strong. Who is strong?', 'The big bear'],
  [912, 'A man liked a car. The man did not like the car?', False],

  [913, 'A man liked a car which a woman bought. The car was red. A man liked a car?', True],
  [914, 'A man liked a car which a woman bought. The car was red. The man liked the car?', True],
  [915, 'A man liked a car which a woman bought. The car was red. The man liked a red car?', True],
  [916, 'A man liked a car which a woman bought. The car was red. The man liked the bike?', None],
  [917, 'A man liked a car which a woman bought. The car was red. The man liked a black car?', None],
  [918, 'A man liked a car which a woman bought. The car was red. The man liked the red car?', True],

  # -- indefinite subject with which-clause --

  [919, 'A man had a car which a woman bought. A man had a car which a woman bought?', True],
  [920, 'A man had a car a woman bought. A man had a car which a woman bought?', True],
  [921, 'A man had a car which a woman bought. A man had a car which a woman liked?', None],
  [922, 'A man had a car which a woman bought. A man had a car which a man bought?', None],
  [923, 'A man had a car a woman bought. A woman bought a car?', True],
  [924, 'A man had a car a woman bought. The woman bought a car?', True],
  [925, 'A man had a car a woman bought. The woman did not buy a car?', False],
  [926, 'A man had a car a woman bought. A man had a bike?', None],
  [927, 'A man had a car a woman bought. A woman bought a red car?', None],
  [928, 'A man had a car a woman bought. A man bought a car?', None],
  [929, 'A man had a car a woman bought. The man did not have a car?', False],

  # -- indefinite drove + which --

  [930, 'A man drove a car which a woman bought. A man drove a car which a woman bought?', True],
  [931, 'A man drove a car a woman bought. A man drove a car which a woman bought?', True],
  [932, 'A man drove a car which a woman bought. A man drove a car a woman bought?', True],
  [933, 'A man drove a car which a woman bought. A man drove a car which a woman liked?', None],
  [934, 'A man drove a car which a woman bought. A man drove a car?', True],
  [935, 'A man drove a car which a woman bought. A man drove the car?', True],
  [936, 'A man drove a car which a woman bought. A woman drove the car?', None],
  [937, 'A man drove a car which a woman bought. A woman bought a car?', True],
  [938, 'A man drove a car which a woman bought. A woman bought the car?', True],

  [939, 'A man had a car which a woman bought. A man had a car?', True],
  [940, 'A man had a car which a woman bought. A man had the car?', True],
  [941, 'A man had a car which a woman bought. A woman bought a car?', True],
  [942, 'A man had a car which a woman bought. A woman bought the car?', True],

  # -- which-clause with follow-up facts --

  [943, 'A man had a car which a woman bought. The car was red. A man had a car?', True],
  [944, 'A man had a car which a woman bought. The car was red. The man had the car?', True],
  [945, 'A man had a car which a woman bought. The car was red. The man had a red car?', True],
  [946, 'A man had a car which a woman bought. The car was red. The man had the bike?', None],
  [947, 'A man had a car which a woman bought. The car was red. The man had a black car?', None],
  [948, 'A man had a car which a woman bought. The car was red. The man had the red car?', True],
  [949, 'A man had a car which a woman bought. The car was red. The man had the car which a woman bought?', True],
  [950, 'A man had a car which a woman bought. The car was red. The man had the red car which a woman bought?', True],
  [951, 'A man had a car which a woman bought. The car was red. The man had a car which a boy bought?', None],
  [952, 'A man had a car which a woman bought. The car was red. A man had a red car which a woman bought?', True],
  [953, 'A man had a car which a woman bought. The car was red. The man did not have the red car which a woman bought?', False],

  [954, 'A man had a car which he bought. The car was red. The man bought the red car?', True],
  [955, 'A man had a car which he bought. The car was red. A man bought a red car?', True],

  # -- nested who/which clauses --

  [956, 'Bears who eat fish which are big are strong. John is a bear. John eats fish. John is strong?', None],
  [957, 'Bears who eat fish which are big are strong. John is a bear. John eats big apples. John is strong?', None],

  # -- nested who+which clauses --

  [958, """A man who ate breakfast liked a car which a woman bought. The car was red.
     A man who ate breakfast liked a red car which a woman bought?""", True],
  [959, """A man who ate breakfast liked a car.
     The man ate breakfast?""", True],
  [960, """A man who ate breakfast liked a car which a woman bought. The car was red.
     The man who ate breakfast liked the red car which the woman bought?""", True],
  [961, """A man who ate breakfast liked a car which a woman bought. The car was red.
     The man who ate breakfast liked the red car which a woman bought?""", True],

  [962, 'A man liked a car which a woman bought. The car was red. Who liked a red car?', 'The man'],

  [963, 'A man liked a car which a nice woman bought. The car was red. Who bought the red car?', 'The nice woman'],
  [964, 'A man liked a car which a nice woman bought. The car was red. Who bought a car?', 'The nice woman'],
  [965, 'A man liked a car which a nice woman bought. The car was red. Who was nice?', 'The woman'],
  [966, 'A man liked a car which a nice woman bought. The car was red. Who was nice and bought a car?', 'The woman'],
  [967, 'A man liked a car which a nice woman bought. The car was red. Who bought the black car?', None],

  # -- complex: who + which + follow-up --

  [968, """A man who ate breakfast had a car which a woman bought. The car was red.
     A man who ate breakfast had a red car which a woman bought?""", True],
  [969, """A man who ate breakfast had a car.
     The man ate breakfast?""", True],
  [970, """A man who ate breakfast had a car which a woman bought. The car was red.
     The man who ate breakfast had the red car which the woman bought?""", True],
  [971, """A man who ate breakfast had a car which a woman bought. The car was red.
     The man who ate breakfast had the red car which a woman bought?""", True],

# == AMBIGUOUS MODIFIER SCOPE ==

  # -- manner adverb --

  [972, 'John ate the apple quickly. How did John eat the apple?', 'Quickly.'],
  [973, 'John ate the apple quickly. Did John eat a banana?', None],
  [974, 'Mary visited London in September. When did Mary visit London?', 'In September.'],
  [975, 'Mary visited London in September. Did Mary visit Paris?', None],

  # -- adjectival modifier --

  [976, 'The blue bird sang a beautiful song. What color was the bird?', 'Blue.'],
  [977, 'The blue bird sang a beautiful song. Was the bird red?', False],
  [978, 'The tall man walked into the small room. Who walked into the room?', ['The tall man.', 'The man.']],
  [979, 'John works at the hospital every day. Where does John work?', 'At the hospital.'],
  [980, 'John works at the hospital every day. Does John work at the school?', None],

  # -- instrument PP --

  [981, 'John ate berries with the help of a spoon. John ate berries with the help of a spoon?', True],
  [982, 'John ate berries with the help of a spoon. John ate berries with the help of a spade?', None],

  # -- with-PP ambiguity --

  [983, 'John saw the man with a telescope. John saw the man?', True],

  # -- in-PP ambiguity --

  [984, 'John saw the bird in the garden. John saw the bird?', True],
  [985, 'John saw the bird in the garden. The bird was in the garden?', True],
  [986, 'John saw the bird in the garden. Did John see a fish in the garden?', None],

  # -- on-PP ambiguity --

  [987, 'John ate the pizza on the table. Where was the pizza?', 'On the table.'],
  [988, 'John ate the pizza on the table. Was the pizza on the floor?', False],
  [989, 'John ate the pizza on the table. Did John eat a sandwich?', None],

  [990, 'The cat in the hat sat on the mat. Where was the cat?', ['In the hat.', 'On the mat.']],
  [991, 'Mary put the book on the shelf in the library. Where is the shelf?', 'In the library.'],
  [992, 'Mary put the book on the shelf in the library. Did Mary put a magazine on the shelf?', None],

  # -- under-PP --

  [993, 'Mary found the key under the table. Mary found the key?', True],
  [994, 'Mary found the key under the table. The key was under the table?', True],
  [995, 'Mary found the key under the table. Was the key on the table?', False],

  [996, 'Tom put the book on the chair. The book was on the chair?', True],
  [997, 'Eve kept the milk in the fridge. The milk was in the fridge?', True],

  # -- from-PP --

  [998, 'John met the girl from Paris. John met the girl?', True],
  [999, 'John met the girl from Paris. The girl was from Paris?', True],
  [1000, 'Mary called the boy in the kitchen. Mary called the boy?', True],
  [1001, 'Mary called the boy in the kitchen. The boy was in the kitchen?', True],

  # -- classic PP-attachment ambiguity --

  [1002, 'John shot an elephant in his pyjamas. John shot in his pyjamas?', True],

  [1003, 'John ate berries in a forest with a spoon. John ate berries in a forest with a spoon?', True],
  [1004, 'John ate berries in a forest with a spoon. John ate berries in a field?', None],
  [1005, 'John ate berries in a forest with a spoon. John ate berries in a nice forest with a spoon?', None],
  [1006, 'John ate berries in a forest with a spoon. John ate berries in a nice forest?', None],
  [1007, 'John ate berries in a forest with a spoon. John ate berries with a spoon in a nice forest?', None],

# == PASSIVE VOICE ==

  # -- basic passive --

  [1008, 'John is defeated. Mike is defeated?', None],
  [1009, 'John is defeated. John is defeated?', True],
  [1010, 'John is defeated. Who is defeated?', 'John'],
  [1011, 'John is defeated. John is not defeated?', False],
  [1012, 'John and Mike were defeated. Who defeated John?', None],
  [1013, 'John and Mike were defeated. Who defeated John and Mike?', None],

  [1014, 'An apple was eaten. John ate a pear. What was eaten?', ['The apple and the pear.', 'An apple and a pear.', 'An apple.', 'A pear.']],
  [1015, 'John was nice and defeated. John was nice and defeated?', True],
  [1016, 'John was nice and defeated. John was nice?', True],
  [1017, 'John was defeated. John was defeated?', True],

  # -- active/passive equivalence --

  [1018, 'Clinton defeated Dole. Clinton defeated Dole?', True],
  [1019, 'Clinton defeated Dole. Clinton defeated Mike?', None],
  [1020, 'Dole was defeated by Clinton. Dole was defeated by Clinton?', True],
  [1021, 'Dole was defeated by Clinton. Dole was defeated by Mike?', None],
  [1022, 'Clinton defeated Dole. Dole was defeated by Clinton?', True],
  [1023, 'Clinton defeated Dole. Dole was defeated by Mike?', None],
  [1024, 'Dole was defeated by Clinton. Clinton defeated Dole?', True],
  [1025, 'Dole was defeated by Clinton. Mike defeated Dole?', None],

  # -- passive with by-phrase --

  [1026, 'The window was broken by John. John broke the window?', True],
  [1027, 'The window was broken by John. Did Mary break the window?', None],
  [1028, 'The song was sung by Mary. Mary sang the song?', True],
  [1029, 'The letter was written by Eve. Eve wrote the letter?', True],
  [1030, 'The letter was written by Eve. Did Tom write the letter?', None],
  [1031, 'The house was built by Tom. Tom built the house?', True],
  [1032, 'The house was built by Tom. Tom destroyed the house?', None],
  [1033, 'The bicycle was repaired by Anna. Anna repaired the bicycle?', True],
  [1034, 'The bicycle was repaired by Anna. Anna broke the bicycle?', None],
  [1035, 'The cake was eaten by the child. The child ate the cake?', True],
  [1036, 'The ball was kicked by Mike. Mike kicked the ball?', True],
  [1037, 'The ball was kicked by Mike. Did Mike catch the ball?', None],
  [1038, 'The tree was cut by the farmer. The farmer cut the tree?', True],
  [1039, 'The book was read by Sara. Sara read the book?', True],
  [1040, 'The book was read by Sara. Did Sara write the book?', None],
  [1041, 'The car was washed by Paul. Paul washed the car?', True],
  [1042, 'The room was cleaned by the maid. The maid cleaned the room?', True],
  [1043, 'The picture was painted by Leo. Leo painted the picture?', True],

  # -- agentless passive --

  [1044, 'The window was broken. John broke the window?', None],
  [1045, 'The letter was written. Mary wrote the letter?', None],
  [1046, 'The cake was eaten. Who ate the cake?', None],
  [1047, 'The room was cleaned. Who cleaned the room?', None],
  [1048, 'The glass was broken by the boy. Who broke the glass?', 'The boy.'],

  # -- passive ditransitive --

  [1049, 'Mary was given a promotion. Who received a promotion?', 'Mary.'],
  [1050, 'A promotion was given to Mary. What did Mary get?', 'A promotion.'],
  [1051, 'The city was destroyed. Is the city destroyed?', True],
  [1052, 'The city was destroyed. Is the city intact?', False],
  [1053, 'The mouse was chased by the cat. Who was the cat chasing?', 'The mouse.'],
  [1054, 'The bill was paid by John. Did John pay the bill?', True],
  [1055, 'The bill was paid by John. Did Mary pay the bill?', None],

# == SUBORDINATE CLAUSES ==

  # -- reported speech --

  [1056, 'John said that Mary left. Mary left?', True],
  [1057, 'John said that Mary left. Did Mary stay?', None],
  [1058, 'Eve reported that Tom arrived. Tom arrived?', True],
  [1059, 'Eve reported that Tom arrived. Did Tom depart?', None],
  [1060, 'Anna announced that the show started. The show started?', True],
  [1061, 'The guide explained that the road was closed. Was the road open?', False],

  # -- infinitival purpose clause --

  [1062, 'John went to the shop to buy bread. John went to the shop?', True],
  [1063, 'John went to the shop to buy bread. John bought bread?', None],
  [1064, 'John went to the shop to buy bread. Did John go to the bank?', None],

  [1065, 'Mary opened the window to let in air. Mary opened the window?', True],
  [1066, 'Mary opened the window to let in air. Mary did not open the window?', False],
  [1067, 'Mary opened the window to let in air. Air came in?', None],

  # -- concessive: although --

  [1068, 'Although John was tired, he finished the work. John was tired?', True],
  [1069, 'Although John was tired, he finished the work. John finished the work?', True],
  [1070, 'Although John was tired, he finished the work. John did not finish the work?', False],
  [1071, 'Although John was tired, he finished the work. Was the work difficult?', None],

  # -- concessive: though --

  [1072, 'Though Mary was ill, she traveled. Mary was ill?', True],
  [1073, 'Though Mary was ill, she traveled. Mary traveled?', True],
  [1074, 'Though Mary was ill, she traveled. Mary did not travel?', False],
  [1075, 'Though Mary was ill, she traveled. Did Mary recover?', None],

  # -- sentence adverbials --

  [1076, 'Fortunately, John found the key. John found the key?', True],
  [1077, 'Fortunately, John found the key. John did not find the key?', False],
  [1078, 'Fortunately, John found the key. Did John find the lock?', None],

  [1079, 'Sadly, Mary lost the letter. Mary lost the letter?', True],
  [1080, 'Unexpectedly, the door opened. The door opened?', True],
  [1081, 'Unexpectedly, the door opened. The door did not open?', False],
  [1082, 'Apparently, Tom left early. Tom left early?', True],

  [1083, 'Mary said that she was tired. Who was tired?', 'Mary.'],
  [1084, 'Mary said that she was tired. Was Mary happy?', None],
  [1085, 'A surgeon, Dr. Smith, entered the room. Who entered the room?', ['Dr. Smith.', 'A surgeon.']],
  [1086, 'The horse kept in the stable was calm. The horse was in the stable?', True],

# == ELLIPSIS & GAPPING ==

  # -- gapping --

  [1087, 'John likes tea and Mary coffee. What does Mary like?', 'Coffee.'],
  [1088, 'John likes tea and Mary coffee. Does Mary like tea?', None],

  # -- locative gapping --

  [1089, 'John went to Paris and Mary to London. Where did Mary go?', ['London.', 'To London.']],
  [1090, 'Paul ate a sandwich and Bill a salad. What did Bill eat?', 'A salad.'],
  [1091, 'Paul ate a sandwich and Bill a salad. Did Paul eat a salad?', None],

  # -- VP ellipsis with did-too --

  [1092, 'John saw the doctor and Mary did too. Did Mary see the doctor?', True],
  [1093, 'John saw the doctor and Mary did too. Did Mary see the dentist?', None],
  [1094, 'John bought a book, and Bill said Peter did too. Did Bill say Peter bought a book?', True],

  # -- conditional did-too --

  [1095, 'If John wrote a report, then Bill did too. John wrote a report. Did Bill write a report?', True],
  [1096, 'If John wrote a report, then Bill did too. John wrote a report. Did Bill write a novel?', None],

# == ACTION MODES & HABITS ==

  # -- action with location --

  [1097, 'Bears eat berries in a forest. Bears eat berries in a forest?', True],
  [1098, 'Bears eat berries in a forest. Bears eat berries in a big forest?', None],
  [1099, 'Bears do not eat berries in a forest. Bears eat berries in a forest?', False],

  # -- action with manner adverb --

  [1100, 'Bears quickly eat berries in a forest. Bears eat berries?', True],
  [1101, 'Bears quickly eat berries in a forest. Bears quickly eat berries?', True],
  [1102, 'Bears quickly eat berries in a forest. Bears slowly eat berries?', None],

  [1103, 'Bears eat red berries in a forest. Bears eat berries in forest?', True],
  [1104, 'Bears do not eat red berries in a forest. Bears eat red berries in forest?', False],

  [1105, 'Bears eat berries in a deep forest. Bears eat berries?', True],
  [1106, 'Bears eat berries in a deep forest. Bears eat berries in a deep forest?', True],
  [1107, 'Bears eat berries in a deep forest. Bears eat berries in a forest?', True],
  [1108, 'Bears eat berries in a deep forest. Bears eat berries in a shallow forest?', None],

  # -- action with modified arguments --

  [1109, 'Bears eat red berries in a deep forest. John is a bear. John eats red berries in a deep forest?', True],
  [1110, 'Bears eat red berries in a deep forest. John is a bear. John eats no berries?', False],
  [1111, 'Bears eat berries in a deep forest. John is a bear. John eats berries in a shallow forest?', None],
  [1112, 'Bears quickly eat berries in a deep forest. John is a bear. John quickly eats berries in a deep forest?', True],

  [1113, """If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John quickly eats berries in a deep forest. John is hungry?""", True],
  [1114, """If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John eats berries in a deep forest. John is hungry?""", None],
  [1115, """If a bear quickly eats berries in a deep forest, it is hungry. John is a fox.
     John quickly eats berries in a deep forest. John is hungry?""", None],

  [1116, """If a bear eats berries in a forest, it is hungry. John is a brown bear.
      John quickly eats berries in a deep forest. Who is hungry?""", 'John.'],
  [1117, """If a bear eats berries in a forest, it is hungry. John is a brown bear.
      John draws berries in a deep forest. Who is hungry?""", None],
  [1118, """If a bear eats, it is hungry. John is a brown bear.
      John quickly eats berries in a deep forest. Who is hungry?""", 'John.'],

  # -- habitual location --

  [1119, 'Penguins live in the water. Penguins live in the water?', True],
  [1120, 'Penguins live in the water. Penguins live in water?', True],
  [1121, 'Penguins live in the water. Penguins live in stone?', None],
  [1122, 'Penguins live in the water. Penguins live in the stone?', None],
  [1123, 'Penguins live in water. Penguins live in water?', True],
  [1124, 'Penguins live in water. Penguins live in stone?', None],
  [1125, 'Penguins live in water. Penguins live in the stone?', None],

  [1126, 'Penguins happily live in cold water. Penguins live in water?', True],
  [1127, 'Penguins happily live in cold water. Penguins live in cold water?', True],

  [1128, 'Bears eat berries in a forest. Bears eat berries in forest?', True],
  [1129, 'Bears eat berries in a forest. Bears do not eat berries in forest?', False],
  [1130, 'Bears eat berries in a forest. Bears eat berries in a field?', None],
  [1131, 'Bears eat berries in a forest. Bears eat berries?', True],

# == TRANSFER OF POSSESSION (GIVE/TAKE) ==

  # -- basic give/receive --

  [1132, 'John gave Mary a book. Who received a book?', 'Mary.'],
  [1133, 'John gave Mary a book. Did John receive a book?', None],
  [1134, 'John gave a book to Mary. What did Mary receive?', ['A book.', 'The book.']],
  [1135, 'John gave a book to Mary. Did Eve receive a book?', None],

  # -- hand: transfer variant --

  [1136, 'Anna handed Mark a key. Mark got a key?', True],
  [1137, 'Anna handed a key to Mark. Anna handed Mark a key?', True],
  [1138, 'Anna handed a key to Mark. Did Anna hand Mark a lock?', None],

  # -- show/see inference --

  [1139, 'The teacher showed the students the map. Who saw the map?', ['The students.', 'The teacher and the students.']],
  [1140, 'The teacher showed the students the map. Did the teacher show a book?', None],
  [1141, 'The teacher showed the map to the students. What did the teacher show?', 'The map.'],

  # -- tell: communication transfer --

  [1142, 'John told Mary a story. Mary heard a story?', True],
  [1143, 'John told Mary a story. Did Mary tell John a story?', None],
  [1144, 'John told a story to Mary. Who heard a story?', 'Mary.'],

  [1145, 'The guide offered the tourists tea. Did the guide offer coffee?', None],

  # -- for-benefactive --

  [1146, 'The chef cooked a meal for the guests. Who was the meal for?', 'The guests.'],
  [1147, 'The chef cooked a meal for the guests. Did the chef eat the meal?', None],

  # -- reflexive transfer --

  [1148, 'Susan bought herself a new car. Who owns a new car?', 'Susan.'],
  [1149, 'Susan bought herself a new car. Did Tom buy a car?', None],
  [1150, 'Susan bought a new car for herself. What did Susan buy?', ['A new car.', 'A car.']],

  [1151, 'John gave Mary a book. Mary got a book?', True],
  [1152, 'John gave Mary a book. Did Mary give John a book?', None],
  [1153, 'John gave a book to Mary. Mary got a book?', True],

  [1154, 'Eve sent Tom a letter. Did Tom send Eve a letter?', None],
  [1155, 'Eve sent a letter to Tom. Who got a letter?', 'Tom.'],
  [1156, 'The teacher showed the students a map. The students saw a map?', True],
  [1157, 'The teacher showed the students a map. Did the students see a globe?', None],
  [1158, 'The teacher showed a map to the students. Who saw a map?', ['The students.', 'The teacher and the students.']],

  # -- give with modified object --

  [1159, 'John gave Mary a red book. Mary got a red book?', True],
  [1160, 'John gave Mary a red book. Mary got a blue book?', None],
  [1161, 'Eve sent Tom a long letter. Tom got a short letter?', None],
  [1162, 'Anna handed Mark a silver key. Mark got a silver key?', True],
  [1163, 'The teacher showed the students a large map. The students saw a large map?', True],
  [1164, 'The teacher showed the students a large map. Did the students see a small map?', None],

  [1165, 'Bears eat red berries in a forest. Bears eat red berries in forest?', True],
  [1166, 'Bears eat red berries in a forest. Bears eat yellow berries in forest?', None],

# == TENSE, ASPECT & CHANGE OF STATE ==

  # -- did-emphasis --

  [1167, 'A man did have a car. A man had a car?', True],
  [1168, 'A man had a car. A man did have a car?', True],
  [1169, 'The man has a car. The man does have a car?', True],
  [1170, 'A man had a car. A man has a car?', True],
  [1171, 'A man had a car. The man has a car?', True],

  # -- perfective aspect --

  [1172, 'John has finished his homework. Is the homework finished?', True],
  [1173, 'John has finished his homework. Is the homework unfinished?', False],
  [1174, 'John has finished his homework. Has John finished his project?', None],

  # -- progressive aspect --

  [1175, 'Mary was reading a book when the phone rang. Did the doorbell ring?', None],

  # -- future tense --


  # -- present for scheduled events --

  [1176, 'The train leaves at noon. When does the train leave?', 'At noon.'],

  # -- temporal subordinate: before --

  [1177, 'Before John left, he locked the door. John locked the door?', True],
  [1178, 'Before John left, he locked the door. John left?', True],
  [1179, 'Before John left, he locked the door. Did John lock the window?', None],

  # -- temporal subordinate: after --

  [1180, 'After Mary arrived, she called Tom. Mary arrived?', True],
  [1181, 'After Mary arrived, she called Tom. Mary called Tom?', True],
  [1182, 'After Mary arrived, she called Tom. Did Mary call Eve?', None],

  # -- temporal subordinate: when --

  [1183, 'When Eve entered the house, she smiled. Eve entered the house?', True],
  [1184, 'When Eve entered the house, she smiled. Eve did not enter the house?', False],
  [1185, 'When Eve entered the house, she smiled. Eve smiled?', True],

  # -- temporal subordinate: while --

  [1186, 'While John was cooking, Mary read a book. John cooked?', True],
  [1187, 'While John was cooking, Mary read a book. Did John read a book?', None],
  [1188, 'While John was cooking, Mary read a book. Mary read a book?', True],

  [1189, 'As Tom walked home, it rained. Tom walked home?', True],
  [1190, 'As Tom walked home, it rained. It rained?', True],
  [1191, 'As Tom walked home, it rained. Did it snow?', None],

  # -- temporal subordinate: once --

  [1192, 'Once Anna found the key, she opened the box. Anna found the key?', True],
  [1193, 'Once Anna found the key, she opened the box. Anna opened the box?', True],
  [1194, 'Once Anna found the key, she opened the box. Did Anna close the box?', None],

  # -- temporal subordinate: since --

  [1195, 'Since Mike lost his ticket, he stayed outside. Mike lost his ticket?', True],
  [1196, 'Since Mike lost his ticket, he stayed outside. Mike stayed outside?', True],
  [1197, 'Since Mike lost his ticket, he stayed outside. Did Mike find his ticket?', None],

  [1198, 'Until Sara arrived, John waited. Sara arrived?', True],
  [1199, 'Until Sara arrived, John waited. John waited?', True],

  [1200, 'After John bought a car, he washed it. John bought a car?', True],
  [1201, 'After John bought a car, he washed it. John washed the car?', True],
  [1202, 'After John bought a car, he washed it. Did John sell the car?', None],

  [1203, 'Before Mary wrote a letter, she found a pen. Mary found a pen?', True],
  [1204, 'Before Mary wrote a letter, she found a pen. Did Mary find a pencil?', None],

  # -- change-of-state verbs --

  [1205, 'John stopped smoking. Did John smoke in the past?', True],
  [1206, 'John stopped smoking. Does John smoke now?', False],
  [1207, 'Mary started the car. Was the car running before?', False],
  [1208, 'The rain continued. Was it raining earlier?', True],

# == SPATIAL LOGIC & WHERE QUERIES ==

  # -- basic location assertions --

  [1209, 'We are in the barn. We are in the barn?', True],
  [1210, 'We are in the barn. We are in the shop?', None],
  [1211, 'We are in the barn. We are on the barn?', None],

  [1212, 'Agatha is in trouble. Agatha is in trouble?', True],
  [1213, 'Agatha is in trouble. Agatha is in the barn?', None],
  [1214, 'Agatha is in trouble. Agatha is through trouble?', None],

  # -- existential location --

  [1215, 'There is a ghost in the room. There is a ghost in the room?', True],
  [1216, 'There is a ghost in the room. A ghost is in the room?', True],
  [1217, 'There is a ghost in the room. There is a lamp in the room?', None],
  [1218, 'There is a ghost in the room. There is a ghost in the barn?', None],

  [1219, 'These links present the many viewpoints that existed. These links present the lemmas that existed?', None],

  # -- basic where-questions --

  [1220, 'John is in a box. Mark is in a house. Where is John?', ['In the box.', 'In a box.']],
  [1221, 'John is in a box. Mark is in a house. Where is Mark?', 'In the house.'],
  [1222, 'John is on a box. Mark is on a house. Where is John?', ['On the box.', 'On a box.']],
  [1223, 'John is on a box. Mark is on a house. Where is Mark?', ['On the house.', 'On a house.']],
  [1224, 'John is at a box. Mark is at a house. Where is John?', ['At the box.', 'At a box.']],
  [1225, 'John is at a box. Mark is at a house. Where is Mark?', ['At the house.', 'At a house.']],

  [1226, 'John is near a box. Mark is near a house. Where is John?', ['Near the box.', 'Near a box.']],
  [1227, 'John is near a box. Mark is near a house. Where is Mark?', ['Near the house.', 'Near a house.']],
  [1228, 'John is under a box. Mark is under a house. Where is John?', ['Under the box.', 'Under a box.']],
  [1229, 'John is under a box. Mark is under a house. Where is Mark?', ['Under the house.', 'Under a house.']],
  [1230, 'John is above a box. Mark is above a house. Where is John?', ['Above the box.', 'Above a box.']],
  [1231, 'John is above a box. Mark is above a house. Where is Mark?', ['Above the house.', 'Above a house.']],
  [1232, 'A car is in a box and in a house. Where is the car?', ['In the house and in the box.', 'In a box and in a house.', 'In a house.', 'In a box.']],
  [1233, 'A car was in a box and in a house. Where was the car?', ['In the house and in the box.', 'In a box and in a house.', 'In a box.', 'In a house.']],
  [1234, 'John is in the box and in the red house. Where is John?', 'In the box and in the red house.'],

  # -- conjunction in location --

  [1235, 'John is in a box and house. Mark is near the house. Where is John?', ['In the house and in the box.', 'In a box and house.', 'In a box.']],
  [1236, 'John is in a box and house. Mark is near the house. Where is Mark?', 'Near the house.'],

  # -- containment and transitivity --

  [1237, """Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. Tallinn is in what?""", ['Earth, Europe and Estonia.', 'Estonia.', 'Europe.', 'Earth.']],
  [1238, """Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. What is not in Estonia?""", 'Riga.'],
  [1239, """Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. Riga is in Estonia?""", False],

  [1240, '"Riga is outside America. Riga is not in what?', 'America.'],
  [1241, '"Riga is not in America. What is not in America?', 'Riga.'],

  # -- spatial rules --

  [1242, """If a city is in Estonia, it is an Estonian city. Tallinn is in Estonia. Tallinn is a city.
     What is an Estonian city?""", 'Tallinn.'],
  [1243, """Cities in Estonia are estonian. Tallinn is in Estonia. Tallinn is a city.
    What is an Estonian city?""", 'Tallinn.'],

  # -- spatial conditionals --

  [1244, 'If John is in a box, he is in the house. John is in the box. Mark is not in the box. Where is John?', ['In the box and in the house.', 'In the house.', 'In the box.']],
  [1245, 'If a car is in a box, the car is in the house. A red car is in the box. Where is a car?', ['In the box and in the house.', 'In the house.', 'In the box.']],
  [1246, 'John is not in the box. John is in the red house. Where is John?', 'In the red house.'],
  [1247, 'The black car is not in the box. The car is in the red house. Where is the car?', 'In the red house.'],
  [1248, 'John is in a box. John is near a spoon. John is on the floor. Where is John?', ['Near the spoon, in the box and on the floor.', 'In a box.', 'On the floor.', 'Near a spoon.', 'In a box on the floor.']],
  [1249, 'John is in a box. John is near a spoon. John is on the floor. John is not in the box. Where is John?', ['On the floor and near the spoon.', 'On the floor.']],
  [1250, 'John is in a box. John is near a spoon. John is on the floor. John is not in the box. Where is John?', ['On the floor and near the spoon.', 'On the floor.', 'Near a spoon.']],

  # -- chained location --

  [1251, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the black car?""", ['In the street and in Tallinn.', 'In the street.', 'In Tallinn.']],
  [1252, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the red car?""", 'In the house.'],
  [1253, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is a car?""", ['In the house, in the street and in Tallinn.', 'In the house.', 'In the street.', 'In the house and in the street.', 'In Tallinn.']],
  [1254, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the man?""", ['In the red car and in the house.', 'In the house.', 'In the red car.']],

  # -- nested location --

  [1255, 'John is in the box which is in the red house. Where is John?', ['In the box and in the red house.', 'In the red house.', 'In the box.']],
  [1256, 'John is in the box which is in the red house. Where is the box?', 'In the red house.'],

  [1257, 'John is in the box which is near the red house. Where is John?', ['In the box.', 'Near the red house.', 'In the box near the red house.']],
  [1258, 'John is in the box which is near the red house. Where is the box?', 'Near the red house.'],
  [1259, 'John is in the box near the red house. Where is John?', ['In the box.', 'In the box near the red house.']],

  [1260, 'John is in the box in the red house. Where is John?', ['In the box and in the red house.', 'In the box in the red house.', 'In the box.', 'In the red house.']],
  [1261, 'John is in the box near the red house. Where is the box?', 'Near the red house.'],

  [1262, 'John is in the box at the red house. A box is at a house?', True],
  [1263, 'John is in the box at a red house. The box is at a house?', True],
  [1264, 'John is in the box at a red house. The red box is at a house?', None],
  [1265, 'John is in the box at a red house. The box is at a blue house?', None],
  [1266, 'John is in a box at the red house. A box is at a house?', True],
  [1267, 'John is in a box at the red house. The box is at a house?', True],
  [1268, 'John is in a box at the red house. A box is at the red house?', True],

  # -- location of general terms --

  [1269, 'Birds are in the box. Where are birds?', 'In the box.'],
  [1270, 'The birds are in the box. Where are the birds?', 'In the box.'],
  [1271, 'The birds are in the box. Where are birds?', 'In the box.'],

  [1272, 'Birds near Tallinn are nice. John is near Tallinn. What is near Tallinn?', ['A bird near Tallinn', 'John.', 'John and birds.']],
  [1273, 'Birds near Tallinn are nice. John is near Tallinn. Who is near Tallinn?', 'John'],
  [1274, 'Birds near Tallinn are nice. John is near Tallinn. What is nice?', 'A bird near Tallinn'],
  [1275, 'Birds near Tallinn are nice. John is near Tallinn. John is a bird. Who is nice?', 'John'],

  [1276, 'Birds near Tallinn are nice. John is a bird who is near Tallinn. Who is nice?', 'John'],

  # -- location of actions --

  [1277, 'John ate candy in a house. John ate meat in a room. Where did John eat candy?', 'In a house'],
  [1278, 'John ate candy in a house. John ate meat in a room. Where did John eat meat?', 'In a room'],
  [1279, 'John ate candy in a house. John ate meat at a room. Where did John eat?', ['At a room and in a house', 'In a house and at a room.', 'In a house.', 'At a room.']],

  [1280, 'John jumped high in a room. John jumped low near the garage. Where did John jump?', ['In a room and near the garage', 'In a room.', 'Near the garage.']],
  [1281, 'John jumped high in a room. John jumped low near the garage. Where did John jump high?', 'In a room'],
  [1282, 'John jumped high in a room. John jumped low near the garage. Where did John jump low?', 'Near the garage'],
  [1283, 'John jumped high in a room. John jumped low near the garage. Where did John jump quickly?', None],

  # -- location via relative clause --

  [1284, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate?', True],
  [1285, 'Bears ate berries in a forest which was seen by Mary. Mary saw the forest where the bears ate?', True],

  [1286, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears drank?', None],
  [1287, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate berries?', True],
  [1288, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate honey?', None],

  [1289, 'John lives in a red car bought by Mary. Mary bought the car where John ate?', None],
  [1290, 'John lives in a red car bought by Mary. Mary bought the car where Mike lives?', None],

  # -- temporal-spatial --

  [1291, 'During 1800, John jumped in a house. During 1800, John jumped?', True],
  [1292, 'During 1800, John jumped in a house. During 1801, John jumped?', None],
  [1293, 'During 1800, John jumped in a house. When did John jump?', ['During the year 1800', 'During 1800.']],
  [1294, 'During 1800, John jumped in a house. Where did John jump?', 'In a house'],

  [1295, 'Before 1900, John jumped in a house. When did John jump?', ['Before the year 1900', 'Before 1900.']],
  [1296, 'Before 1900, John jumped in a house. After 1902, John ate in a house. When did John jump?', ['Before the year 1900', 'Before 1900.']],
  [1297, 'Before 1900, John jumped in a house. After 1902, John sat in a house. When did John sat?', ['After the year 1902', 'After 1902.']],
  [1298, 'On Monday, John jumped in a house. Where did John jump?', 'In a house'],
  [1299, 'On Monday, John jumped in a house. When did John jump?', 'On Monday'],
  [1300, 'The cat slept on the velvet sofa. Where did the cat sleep?', ['On the velvet sofa.', 'On the sofa.']],

  [1301, 'The book that Mary bought is on the table. Where is the book?', 'On the table.'],
  [1302, 'The cake that was on the counter has disappeared. Where was the cake?', 'On the counter.'],
  [1303, 'The cat sat on the mat and purred. Where did the cat sit?', 'On the mat.'],

# == ACTION AND WORLD STATE SEQUENCES ==

  # -- bAbI: single supporting fact --

  [1304, 'John travelled to the hallway. Mary journeyed to the bathroom. Where is John?', ['hallway', 'In the hallway.', 'At the hallway.']],

  [1305, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. Where is Mary?', ['bathroom', 'In the bathroom.', 'At the bathroom.']],
  [1306, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Where is Sandra?', ['kitchen', 'In the kitchen.', 'At the kitchen.']],
  [1307, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Sandra travelled to the hallway. John went to the garden. Where is Sandra?', ['hallway', 'In the hallway.', 'At the hallway.']],
  [1308, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Sandra travelled to the hallway. John went to the garden. Sandra went back to the bathroom. Sandra moved to the kitchen. Where is Sandra?', ['kitchen', 'In the kitchen.', 'At the kitchen.']],

  # -- bAbI: multi-step tracking --

  [1309, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Where is Sandra?', ['hallway', 'In the hallway.', 'At the hallway.']],
  [1310, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Where is Sandra?', ['garden', 'In the garden.', 'At the garden.']],
  [1311, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Where is Daniel?', ['hallway', 'In the hallway.', 'At the hallway.']],
  [1312, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. Where is Sandra?', ['office', 'In the office.', 'At the office.']],
  [1313, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. John travelled to the bathroom. John journeyed to the office. Where is Daniel?', ['office', 'In the office.', 'At the office.']],

  [1314, 'The dog was barking and the cat was too. Was the cat barking?', True],
  [1315, 'Eve planned to travel. Eve traveled?', None],



# == QUESTION LOGIC (WHO/WHAT/WHICH) ==

  [1316, 'John is nice. Is it true that John is nice?', True],
  [1317, 'John is nice. Is it false that John is nice?', False],

  # -- who-is identity questions --

  [1318, 'John Sweeney is a car. John Smith is bad. Who is John Sweeney?', 'A car.'],

  [1319, 'John Sweeney is a car. Who is John?', ['John Sweeney is a car.', 'A car.', 'John Sweeney.']],

  [1320, 'John Sweeney is cool and bought a car. John is a bad baby man. John is not big. Who is John?', ['John Sweeney is a not big cool bad baby man.', 'John Sweeney.', 'A cool baby man.', 'A cool baby and a man.']],

  # -- what/who/whom-of questions --

  [1321, 'Ellen is afraid of John. What is Ellen afraid of?', 'John'],
  [1322, 'Ellen is afraid of John. Who is Ellen afraid of?', 'John'],
  [1323, 'Ellen is afraid of John. Whom is Ellen afraid of?', 'John'],
  [1324, 'Ellen is afraid of John. Ellen is afraid of whom?', 'John'],
  [1325, 'Ellen is afraid of John. Ellen is afraid of who?', 'John'],

  [1326, 'Ellen is fond of John. Who is Ellen afraid of?', None],
  [1327, 'Ellen is fond of John. Whom is Ellen afraid of?', None],
  [1328, 'Ellen is fond of John. Ellen is afraid of who?', None],

  # -- multi-entity who/what questions --

  [1329, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man has an apple?""", 'John'],
  [1330, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which has a pear?""", 'Mike'],
  [1331, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which is bad?""", 'Greg'],
  [1332, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man has a potato?""", None],
  [1333, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man is nice?""", 'John and Mike'],
  [1334, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man is bad?""", 'Greg'],
  [1335, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has a pear?""", 'Mike'],
  [1336, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which bad man has a pear?""", None],
  [1337, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has an apple or a pear?""", 'John and Mike'],
  [1338, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has an apple and a pear?""", None],

  [1339, """Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which animal can fly?""", 'A squirrel'],
  [1340, """Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which animal cannot fly?""", 'A fox'],
  [1341, """Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which can fly?""", 'A squirrel'],

# == IF-THEN INFERENCE ==

  # -- basic if-then --

  [1342, 'If cars are red, elephants are nice. Cars are red. Elephants are nice?', True],
  [1343, 'If cars are red, elephants are nice. Elephants are nice?', None],
  [1344, 'If some cars are red, elephants are nice. John is a red car. Elephants are nice?', True],
  [1345, 'If cars are green, elephants are nice. If elephants are nice, squirrels are red. Cars are green. Squirrels are red?', True],
  [1346, 'If cars have roofs, elephants are nice. Cars have roofs. Elephants are nice?', True],
  [1347, 'If some cars have roofs, elephants are nice. John is a car. John has a roof. Elephants are nice?', True],
  [1348, 'If some car has a roof, elephants are nice. John is a car. John has a roof. Elephants are nice?', True],

  # -- if-then with variables --

  [1349, 'If X is cool then X is red. John is cool. Mike is red?', None],
  [1350, 'If X is cool then X is red. John is cool. John is red?', True],

  [1351, 'If X is cool and X is nice then X is red. John is nice and cool. John is red?', True],
  [1352, 'If X is cool and nice then X is red. John is nice and cool. John is red?', True],
  [1353, 'If X is cool and X is nice then X is red. Mike is nice. Mike is red?', None],

  [1354, 'If X is cool and X is nice then X is red. Mike is cool. Mike is red?', None],

  [1355, """If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike and Mary.
      Who is a child of John?""", 'Mike and Mary'],
  [1356, """If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike, Mary and Eve.
      Who is a child of John?""", 'Mike, Mary and Eve'],
  [1357, """If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike or Mary.
      Who is a child of John?""", 'Mike or Mary'],

  [1358, 'If X1 is a grandfather of Y1, Y1 is not a child of X1. John is a grandfather of Mike. Who is not a child of John?', 'Mike.'],
  [1359, 'If X1 is not a parent of Y1, Y1 is not a child of X1. John is not a parent of Mike. Who is not a child of John?', 'Mike.'],

  [1360, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John. Luke is a grandfather of Mike?""", True],
  [1361, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. Mike is a grandchild of Luke?""", True],
  [1362, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike is male. Mike is a grandson of Luke?""", True],
  [1363, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike and Mickey are male. Who is a grandson of Luke?""", 'Mike and Mickey.'],
  [1364, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike and Mickey are not female. Any person is male or female.
      Who is a grandson of Luke?""", ['Mickey and Mike.', 'Mike and Mickey.']],
  [1365, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike or Mickey is not female. Any person is male or female.
      Who is a grandson of Luke?""", 'Mike or Mickey.'],
  [1366, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike or Mickey are not female. Any person is male or female.
      Who is a grandson of Luke?""", 'Mike or Mickey.'],

  [1367, """If an animal is cool and defeated then it is green.
   John is a cool defeated animal.
   Mike is an animal. Mike is cool. John is green?""", True],
  [1368, """If an animal is cool and defeated then it is green.
   John is a cool defeated animal.
   Mike is an animal. Mike is cool. John is not green?""", False],
  [1369, """If an animal is cool and defeated then it is green.
   John is a defeated animal.
   Mike is an animal. Mike is cool. John is green?""", None],

  [1370, """If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals.
    John is badly defeated. John is weak?""", True],
  [1371, """If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals.
    John is badly defeated. Mike is weak?""", None],
  [1372, """If someone is a nice animal and badly defeated then they are weak. John is a nice animal.
    Mike is badly defeated. Mike is weak?""", None],

  [1373, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. John is green?""", True],
  [1374, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. Who is green?""", 'John'],
  [1375, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. John is not green?""", False],
  [1376, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. Mike is green?""", None],

  [1377, 'If someone is a bird and wounded then they are abnormal. John is wounded. John is a bird. John is abnormal?', True],
  [1378, 'If someone is a bird and wounded then they are abnormal. John is a bird. John is abnormal?', None],

  # -- have in if-then rules --

  [1379, """If an animal has a trunk, it is an elephant. John has a long trunk. John is an animal.
      John is an elephant?""", True],
  [1380, 'If an animal or bird has a tail, it is cute. John has a tail. John is cute?', None],
  [1381, 'If an animal or bird has a tail, it is cute. John is an animal. John has a tail. John is cute?', True],
  [1382, 'If an animal or bird has a tail, it is cute. John is a bird. John has a tail. John is cute?', True],
  [1383, 'If an animal or bird has a tail, it is cute. John is a bird or an animal. John has a tail. John is cute?', True],
  [1384, 'If a bear is nice, it has a tail. John is a nice bear. John has a tail?', True],
  [1385, 'If a big bear is nice, it has a tail. John is a nice bear. John has a tail?', None],
  [1386, 'If a bear is nice and has a trunk, it has a tail. John is a nice bear. John has a trunk. John has a tail?', True],
  [1387, 'If the bear is strong, the fox is nice. The bear is strong. Who is nice?', 'The fox.'],
  [1388, 'If the bear is strong, the fox is nice. The bear is strong. John is a fox. Who is nice?', ['The fox.', 'John.']],

  # -- coordination in conditionals --

  [1389, 'If animal or bird is nice and simple, it is cute. John is cute?', None],
  [1390, 'If animal or bird is nice and simple, it is cute. John is a nice and simple animal. John is cute?', True],
  [1391, 'If animal or bird is nice and simple, it is cute. John is a nice and simple bird. John is cute?', True],
  [1392, 'If animal or bird is nice and simple, it is cute. John is a nice animal. John is cute?', None],

  [1393, 'If a bear who is big is strong, it is nice. John is a big strong bear. John is nice?', True],
  [1394, 'If a bear who is big is strong, it is nice. John is a big bear. John is strong. John is nice?', 'Likely true'],

  [1395, 'If a bear who eats fish is strong, it is nice. John is a bear. John eats fish. John is strong. John is nice?', 'Likely true'],
  [1396, 'If a bear who eats fish is strong, it is nice. John is a bear. John eats carrots. John is strong. John is nice?', None],
  [1397, 'If a bear who eats fish is strong, it is nice. John is a bear. John eats fish. John is nice?', None],

  [1398, 'If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats strong fish. John is white. John is nice?', True],
  [1399, 'If a big bear who eats strong fish is white, it is nice. John is a bear. John eats strong fish. John is white. John is nice?', None],
  [1400, 'If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats strong fish. John is nice?', None],
  [1401, 'If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats yellow fish. John is white. John is nice?', None],

  # -- if-then with family relations --

  [1402, 'If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike. Who is a child of John?', 'Mike.'],

  [1403, 'If John is not very big, John is nice. John is big. John is nice?', None],
  [1404, 'If John is not very big, John is nice. John is very big. John is nice?', None],
  [1405, 'If a bear is not very big, it is nice. John is a big bear. John is nice?', None],
  [1406, 'If a bear is not very big, it is nice. John is a very big bear. John is nice?', None],

# == DEFAULT & DEFEASIBLE REASONING ==

  # -- basic defaults with exceptions --

  [1407, 'Penguins are birds who do not fly. Birds fly. John is a penguin. John flies?', False],
  [1408, 'Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John flies?', False],
  [1409, 'Penguins are birds who do not fly. Birds fly. John is a bird. John flies?', True],
  [1410, 'Penguins are birds. Penguins do not fly. Birds fly. John is a bird. John flies?', True],
  [1411, 'Cars are nice. Cars are not nice?', False],

  [1412, 'Red cars are not nice. Cars are nice. Cars are not nice?', False],
  [1413, 'Red cars are not nice. Cars are nice. Red cars are not nice?', True],
  [1414, 'Red cars are not nice. Cars are nice. What are nice?', ['A car.', 'Non-red cars.']],
  [1415, 'Red cars are not nice. Cars are nice. What are not nice?', 'A red car.'],

  [1416, 'Red cars do not have trunks. Cars have trunks. Cars have trunks?', True],
  [1417, 'Red cars do not have trunks. Cars have trunks. Red cars have trunks?', False],
  [1418, 'Red cars do not have trunks. Cars have trunks. Cars have a trunk?', True],
  [1419, 'Red cars do not have trunks. Cars have trunks. Red cars have a trunk?', False],

  [1420, 'Red cars do not have trunks. Cars have a trunk. Cars have a trunk?', True],
  [1421, 'Red cars do not have trunks. Cars have trunks. John is a car. John has a trunk?', True],
  [1422, 'Red cars do not have trunks. Cars have trunks. John is a red car. John has a trunk?', False],

  # -- Tweety triangle --

  [1423, 'Penguins are birds. Penguins do not fly. Birds fly. Birds fly?', True],
  [1424, 'Penguins are birds. Penguins do not fly. Birds fly. Penguins fly?', False],
  [1425, 'Penguins are birds. Penguins do not fly. Birds fly. Who flies?', 'A bird.'],
  [1426, 'Penguins are birds. Penguins do not fly. Birds fly. Who does not fly?', 'A penguin.'],
  [1427, 'Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John is a bird?', True],
  [1428, 'Penguins are birds. Penguins do not fly. Birds fly. Mike is a bird. Mike is a penguin?', ['Likely false.', 'Probably false.']],

  [1429, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    John does not fly?""", True],
  [1430, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    Mike flies?""", True],
  [1431, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    John runs?""", None],
  [1432, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who does not fly?""", 'John.'],
  [1433, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies?""", 'Mike and Eve.'],
  [1434, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who eats?""", ['John, Mike and Eve.', 'John, Mike, and Eve.', 'Mike and Eve.']],
  [1435, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies and eats?""", 'Mike and Eve.'],
  [1436, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies or eats?""", 'John, Mike and Eve.'],
  [1437, """Birds fly and eat. Baby birds do not fly. John is perhaps a baby.
     Mike and Eve and John are birds. Who flies and eats?""", ['Mike, Eve and likely John', 'Mike and Eve.']],

  [1438, """Bears eat berries. Baby bears do not eat berries. John is a bear.
     John eats berries?""", True],
  [1439, """Bears eat berries. Baby bears do not eat berries. John is a baby bear.
     John eats berries?""", False],
  [1440, """Bears eat berries. Baby bears eat no berries. John is a baby bear.
     John eats berries?""", False],
  [1441, """Bears eat berries. Baby bears do not eat berries. John and Mike are bears.
      John is a baby bear.
      Who eats berries?""", 'Mike.'],

  [1442, """Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds.
      Who can fly?""", 'Mike and Eve.'],
  [1443, """Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds.
      Who can not fly?""", 'John.'],
  [1444, """Bears can eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who can eat berries?""", 'Mike.'],
  [1445, """Bears can eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who can not eat berries?""", 'John.'],

  [1446, 'Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  [1447, 'Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John flies?', False],
  [1448, 'Birds can fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  [1449, 'Birds fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],
  [1450, 'Birds fly. No penguin can fly. Penguins are birds. John is a bird. John flies?', True],
  [1451, 'Birds can fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],

  [1452, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who flies?', 'Mike'],
  [1453, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who does not fly?', 'John'],
  [1454, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who can fly?', 'Mike'],
  [1455, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John'],

  [1456, """Bears eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who eats berries?""", 'Mike.'],
  [1457, """Bears eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who does not eat berries?""", 'John.'],
  [1458, 'Birds can fly. Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John.'],
  [1459, """Bears can eat berries. Baby bears do not eat berries. John and Mike are bears.
      John is a baby bear.  Who can not eat berries?""", 'John.'],
  [1460, 'Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', ['Perhaps John.', 'John.']],

  [1461, 'John is a car. John is bad. Who is John?', ['John is a bad car.', 'A car.']],
  [1462, 'John is a car. John is bad. Who is John?', ['John is a bad car.', 'A car.']],

  [1463, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Mike is big?""", True],
  [1464, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. John is big?""", False],
  [1465, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Who is big?""", 'Mike.'],
  [1466, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Who is not big?""", 'John.'],
  [1467, """Elephants are big. Young elephants are not big.
      Who is big?""", ['An elephant.', 'Elephants that are not young.']],
  [1468, """Elephants are big. Young elephants are not big.
      Who is not big?""", 'A young elephant.'],

# == DEFAULTS WITH EXCEPTIONS (BLOCKING) ==

  # -- default do-actions --

  [1469, 'Bears eat berries. John is a bear. John eats berries?', True],
  [1470, 'Bears eat berries. John is a bear. John eats some berries?', True],
  [1471, 'Bears eat berries. John is a bear. John eats all berries?', None],
  [1472, 'Bears eat all berries. John is a bear. John eats all berries?', True],
  [1473, 'Some bears eat all berries. John is a bear. John eats berries?', None],

  [1474, 'Some bears eat all berries. Some bears eat berries?', True],

  # -- blocking in conditionals --

  [1475, """If a bear eats red berries, it is big. John eats berries. John is a bear.
     John is big?""", None],
  [1476, """If a bear eats red berries, it is big. John eats red berries. John is a bear.
     John is big?""", True],
  [1477, 'If X1 eats berries, it is a bear. John eats red berries. John is a bear?', True],

  # -- default disjunctive actions --

  [1478, 'Birds fly or swim. John is a bird. John swims?', None],
  [1479, 'Birds fly and swim. John is a bird. John swims and flies?', True],

# == UNCERTAINTY & CONFIDENCE ==

  # -- adverbial probability --

  [1480, 'Elephants are probably animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1481, 'Elephants are rarely animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1482, 'Probably elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1483, 'Probably elephants are not animals. John is an elephant. John is an animal?', 'Probably false.'],

  # -- sentence-initial probably --

  [1484, 'Probably elephants have long trunks. John is an elephant. John has a trunk?', 'Probably true.'],
  [1485, 'Probably elephants have no trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  [1486, 'Elephants have probably long trunks. John is an elephant. John has a long trunk?', 'Probably true.'],
  [1487, 'Elephants have probably no trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  [1488, 'Elephants have rarely trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  [1489, 'It is true that elephants have long grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  [1490, 'It is false that elephants have long grey trunks. John is an elephant. Who has a trunk?', None],
  [1491, 'It is probably true that elephants have long grey trunks. John is an elephant. Who has a trunk?', ['Probably John.', 'John.']],
  [1492, """It is probable that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1493, """It is probable that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably false.'],
  [1494, """It is probably true that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1495, """It is probably false that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1496, """It is unlikely that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably false.'],
  [1497, """It is unlikely that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1498, """It is probable that if X1 is not a grandfather of Y1, Y1 is a child of X1. John is not a grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1499, 'Tallinn is probably in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  [1500, 'Tallinn is hardly in Latvia. Tallinn is in Latvia?', 'Likely false.'],
  [1501, 'It is true that Tallinn is in Estonia. Tallinn is in Estonia?', True],
  [1502, 'It is false that Tallinn is in Latvia. Tallinn is in Latvia?', False],
  [1503, 'It is probably true that Tallinn is in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  [1504, 'It is probably false that Tallinn is in Latvia. Tallinn is in Latvia?', 'Probably false.'],
  [1505, 'Probably Tallinn is in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  [1506, 'It is not probable that Tallinn is in Latvia. Tallinn is in Latvia?', 'Probably false.'],

  # -- it is true/false that --

  [1507, 'It is true that elephants are animals. John is an elephant. John is an animal?', True],
  [1508, 'It is false that elephants are animals. John is an elephant. John is an animal?', False],
  [1509, 'It is not true that elephants are animals. John is an elephant. John is an animal?', False],
  [1510, 'It is not false that elephants are animals. John is an elephant. John is an animal?', True],
  [1511, 'It is probably true that elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1512, 'It is probably false that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1513, 'It is probable that elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1514, 'It is not probable that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1515, 'It is unlikely that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1516, 'It is true that John is a child of Mike. John is a child of Mike?', True],
  [1517, 'It is false that John is a child of Mike. John is a child of Mike?', False],

  # -- it is probable/improbable that --

  [1518, 'It is probable that John is a child of Mike. John is a child of Mike?', 'Probably true.'],
  [1519, 'It is probably true that John is a child of Mike. John is a child of Mike?', 'Probably true.'],
  [1520, 'It is improbable that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1521, 'It is not probable that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1522, 'It is unlikely that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1523, 'It is probably false that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1524, 'John is probably a child of Mike. John is a child of Mike?', 'Probably true.'],
  [1525, 'Probably John is a child of Mike. John is a child of Mike?', 'Probably true.'],

  # -- negated universals --

  [1526, 'It is not true that all big yellow cats are strong. Some yellow cats are not strong?', True],
  [1527, 'It is not true that all big yellow cats are strong. Some red cats are not strong?', None],

  [1528, 'John is nice. It is true that John is nice?', True],
  [1529, 'John smokes tobacco with a probability 0.8. What does John smoke?', ['Likely a tobacco', 'Tobacco.']],
  [1530, 'John smokes tobacco with a probability 0.8. John smokes?', 'Likely true'],
  [1531, 'John smokes tobacco with a probability 80 percent. Does John smoke?', 'Likely true'],
  [1532, 'John is a man. John is probably not bad. Who is John?', ['John is a not bad man.', 'A man.']],
  [1533, """Birds fly and eat. Baby birds do not fly. John is hardly a baby bird.
     Mike and Eve and John are birds. Who flies and eats?""", ['Mike, Eve and John', 'Mike, Eve, and John.']],
  [1534, """Birds fly and eat. Baby birds do not fly. John is probably a baby bird.
     Mike and Eve and John are birds. Who flies and eats?""", 'Mike and Eve'],

  # -- explicit percentage probability --

  [1535, 'John is an elephant with a probability 100 percent. John is an elephant?', True],
  [1536, 'John is an elephant with a probability 0 percent. John is an elephant?', False],
  [1537, 'John is an elephant with a probability 10 percent. John is an elephant?', 'Likely false.'],
  [1538, 'John is an elephant with a probability 90 percent . John is an elephant?', 'Likely true.'],
  [1539, 'John is an elephant with a probability 50 percent. John is an elephant?', None],

  [1540, 'Tallinn is in Estonia with a probability 90 percent. Tallinn is in Estonia?', 'Likely true.'],
  [1541, 'Tallinn is in Latvia with a probability 10 percent. Tallinn is in Latvia?', 'Likely false.'],
  [1542, 'Tallinn is in Latvia with a probability 50 percent. Tallinn is in Latvia?', None],

  [1543, 'Elephants have a trunk with a probability 90 percent. John is an elephant. John has a trunk?', 'Likely true.'],
  [1544, 'Elephants have a trunk with a probability 10 percent. John is an elephant. John has a trunk?', 'Likely false.'],
  [1545, 'Elephants have a trunk with a probability 50 percent. John is an elephant. John has a trunk?', None],
  [1546, 'Elephants have a trunk with a probability 90 percent. John is an elephant. Who has a trunk?', ['Likely John.', 'John.']],

  [1547, 'Elephants probably do not have wings. John is an elephant. Who does not have wings?', ['Probably John.', 'John.']],
  [1548, 'Elephants probably do not have wings. John is maybe an elephant. Who does not have wings?', 'Maybe John.'],
  [1549, 'John probably smokes. John smokes?', 'Probably true'],
  [1550, 'Probably John smokes. John smokes?', 'Probably true'],
  [1551, 'It is probably true that John smokes. John smokes?', 'Probably true'],

  # -- explicit decimal probability --

  [1552, 'John smokes with a probability 90%. John smokes?', 'Likely true'],
  [1553, 'John smokes with a probability 90 percent. John smokes?', 'Likely true'],
  [1554, 'John smokes with a probability 0.9. John smokes?', 'Likely true'],
  [1555, 'John smokes with a probability 0.1. John smokes?', 'Likely false'],
  [1556, 'John smokes tobacco with a probability 0.8. John smokes what?', ['Likely a tobacco', 'Tobacco.']],

  # -- probability with location --

  [1557, 'Probably John is in a cave. Where is John?', ['Probably in the cave', 'Probably in a cave.']],
  [1558, 'John is probably in a cave. Where is John?', ['Probably in the cave', 'Probably in a cave.', 'In a cave.']],

  [1559, 'John is in a cave with a probability 90%. Where is John?', 'Likely in the cave'],
  [1560, 'John is in a cave with a probability 10%. Where is John?', None],
  [1561, 'John is in a cave with a probability 10%. John is in the cave?', 'Likely false'],
  [1562, 'John is in a cave with a probability 10%. John is in a cave?', 'Likely false'],

# == ADVANCED SEMANTIC OPERATORS ==

  # -- implicative: manage --

  [1563, 'John managed to open the door. John opened the door?', True],
  [1564, 'John managed to open the door. John did not open the door?', False],
  [1565, 'Mary managed to solve the puzzle. Mary solved the puzzle?', True],

  # -- implicative: fail --

  [1566, 'Tom failed to catch the bus. Tom caught the bus?', False],
  [1567, 'Eve failed to finish the report. Eve finished the report?', False],

  # -- non-implicative: try --

  [1568, 'John tried to open the door. John opened the door?', None],
  [1569, 'Mary tried to solve the puzzle. Mary solved the puzzle?', None],

  # -- non-implicative: want --

  [1570, 'Tom wanted to leave. Tom left?', None],

  # -- promise --

  [1571, 'John promised to help Mary. John helped Mary?', None],

  # -- decide --

  [1572, 'Mary decided to leave. Mary left?', None],

  # -- refuse --

  [1573, 'Tom refused to eat the soup. Tom ate the soup?', False],
  [1574, 'Tom refused to eat the soup. Did Tom drink the soup?', None],

  # -- forget --

  [1575, 'Eve forgot to lock the door. Eve locked the door?', False],

  # -- raising: seem/appear --

  [1576, 'John seemed tired. John was energetic?', None],

  # -- passive raising --

  [1577, 'John was seen to enter the room. John entered the room?', True],
  [1578, 'John was seen to enter the room. Did John leave the room?', None],
  [1579, 'Mary was heard to sing. Mary sang?', True],

  # -- deontic modality --

  [1580, 'You may enter the building. Do you have permission to enter?', True],

  # -- focus particle: only --

  [1581, 'Only John bought a car. Did Mary buy a car?', False],
  [1582, 'Only John bought a car. Who bought a car?', 'John.'],
  [1583, 'John only eats apples. Does John eat bananas?', False],

  # -- exceptive --

  [1584, 'Everyone except John arrived. Did John arrive?', False],
  [1585, 'All the boxes are red except for the small one. Is the small box red?', False],

  # -- embedded interrogative --

  [1586, 'Mary asked whether it was raining. Does Mary know if it is raining?', None],

  # -- donkey anaphora --


  # -- degree complement: too --


  # -- causative --

  [1587, 'John made Mary cry. Did Mary cry?', True],
  [1588, 'Tom had the mechanic fix his car. Who fixed the car?', 'The mechanic.'],

  # -- cleft sentence --

  [1589, 'It was John who ate the cake. Who ate the cake?', 'John.'],

# == COMPLEX REASONING CHAINS ==

  # -- fear chains --

  [1590, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is emily afraid of?', ['A wolf.', 'wolf', 'Wolves.', 'wolves']],
  [1591, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is winona afraid of?', ['A mouse.', 'mouse', 'Mice.', 'mice']],
  [1592, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is gertrude afraid of?', ['mouse', 'Jessica.']],
  [1593, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is jessica afraid of?', ['A cat.', 'cat', 'Cats.', 'cats']],

  # -- extended fear chains --

  [1594, 'Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is emily afraid of?', 'sheep'],
  [1595, 'Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is jessica afraid of?', ['A cat.', 'cat', 'Cats.', 'cats']],
  [1596, 'Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is gertrude afraid of?', ['A wolf.', 'wolf', 'Wolves.', 'wolves']],

  [1597, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Emily afraid of?""", ['Probably a wolf', 'Wolves.', 'Gertrude.']],
  [1598, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    Who is Emily afraid of?""", ['Probably Gertrude', 'Gertrude.', 'Wolves.']],
  [1599, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What are cats afraid of?""", ['A wolf.', 'wolf', 'Wolves.', 'wolves']],
  [1600, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Winona afraid of?""", ['A mouse.', 'mouse', 'Mice.', 'mice']],




]
