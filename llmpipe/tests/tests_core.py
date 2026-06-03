# Core test suite for the nlpsolver pipeline.
# Tests are organized by linguistic phenomenon, from simple to complex.
#
# Table of contents
#
# PHASE I: FOUNDATIONS
# FUNDAMENTAL TAXONOMY & TYPE LOGIC (8 tests)
# LOGICAL CONNECTIVES (12 tests)
# PROPERTIES & ADJECTIVAL LOGIC (40 tests)
# NUMBER & PLURALITY (13 tests)
#
# PHASE II: REFERENCE & POSSESSION
# COREFERENCE & ANAPHORA (97 tests)
# POSSESSION & HAVE (44 tests)
# DEFINITE DESCRIPTIONS: X OF Y AND POSSESSIVES (40 tests)
# POSSESSION INFERENCE FROM DESCRIPTIONS (130 tests)
# SETS AND COUNTING (28 tests)
# MEASURES (99 tests)
#
# PHASE III: QUANTIFIERS & COMPARISON
# QUANTIFIERS: UNIVERSAL & EXISTENTIAL (31 tests)
# QUANTIFIERS: PROPORTIONAL & NUMERIC (10 tests)
# COMPARATIVES & EQUALITY (9 tests)
#
# PHASE IV: MODIFICATION & STRUCTURE
# COORDINATION (NP, VP, CLAUSAL) (21 tests)
# LISTS AND CONJUNCTIONS (53 tests)
# INTERNAL MODIFICATION (79 tests)
# RELATIVE CLAUSES (273 tests)
# AMBIGUOUS MODIFIER SCOPE (39 tests)
#
# PHASE V: CLAUSE ALTERNATIONS
# PASSIVE VOICE (50 tests)
# SUBORDINATE CLAUSES (32 tests)
# ELLIPSIS & GAPPING (11 tests)
#
# PHASE VI: EVENTS & STATE
# ACTION MODES & HABITS (36 tests)
# TRANSFER OF POSSESSION (GIVE/TAKE) (35 tests)
# TENSE, ASPECT & CHANGE OF STATE (45 tests)
# SPATIAL LOGIC & WHERE QUERIES (96 tests)
# ACTION AND WORLD STATE SEQUENCES (12 tests)
#
# PHASE VII: QUESTIONS
# QUESTION LOGIC (WHO/WHAT/WHICH) (29 tests)
#
# PHASE VIII: REASONING
# IF-THEN INFERENCE (66 tests)
# DEFAULT & DEFEASIBLE REASONING (62 tests)
# DEFAULTS WITH EXCEPTIONS (BLOCKING) (14 tests)
# UNCERTAINTY & CONFIDENCE (84 tests)
# ADVANCED SEMANTIC OPERATORS (39 tests)
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

# == LOGICAL CONNECTIVES ==

  [9, 'John is a man or not a man?', True],
  [10, 'John is a man and not a man?', False],
  [11, 'John is tall or not tall?', True],
  [12, 'John is tall and not tall?', False],
  [13, 'John is a tall man and not a tall man?', False],
  [15, 'John has a car or does not have a car?', True],
  [16, 'John has a car and does not have a car?', False],
  [17, 'John has a car?', None],
  [18, 'John is in Estonia or is not in Estonia?', True],
  [19, 'John is in Estonia and is not in Estonia?', False],
  [20, 'John is in Estonia?', None],

# == PROPERTIES & ADJECTIVAL LOGIC ==

  # -- adjective combos with and/or --

  [21, 'Big or strong elephants are nice. John is a big elephant. John is nice?', True],
  [22, 'Big or strong elephants are nice. John is a big elephant. John is strong. John is nice?', True],
  [23, 'Big or strong elephants are nice. John is an elephant. John is nice?', None],
  [24, 'Big and strong elephants are nice. John is a big elephant. John is a strong elephant. John is nice?', True],
  [25, 'Yellow and green elephants are nice. John is an elephant. John is yellow and green. John is nice?', "Probably true."],
  [26, 'Big and strong elephants are nice. John is a strong elephant. John is nice?', None],
  [27, 'Big and not strong elephants are nice. John is a big elephant. John is a not strong elephant. John is nice?', True],

  # -- degree modifiers: very, somewhat, extremely --

  [28, 'John is very big. John is extremely big?', True],
  [29, 'John is very big. John is very big?', True],
  [30, 'John is very big. John is big?', True],

  [31, 'John is big. John is very big?', None],
  [32, 'John is big. John is big?', True],
  [33, 'John is somewhat big. John is big?', True],
  [34, 'John is somewhat big. John is somewhat big?', True],
  [35, 'John is somewhat big. Mike is very big. Who is very big?', 'Mike'],
  [36, 'John is big. John is not big?', False],
  [37, 'John is very big. John is not very big?', False],
  [38, 'John is very big. John is not big?', False],
  [39, 'John is somewhat big. John is not somewhat big?', False],
  [41, 'John is not very big. John is very big?', False],
  [42, 'A not very big bear is nice. The bear is a very big bear?', False],
  [44, 'John is a not very big bear. John is a very big bear?', False],
  [45, 'John is not a very big bear. John is a very big bear?', False],

  [46, 'A very big mouse is nice. The mouse is a very big mouse?', True],
  [47, 'A very big mouse is nice. The mouse is a big mouse?', True],
  [48, 'A very big mouse is nice. The mouse is very big?', True],
  [49, 'A very big mouse is nice. The mouse is big?', True],

  # -- class-relative properties --

  [50, 'Frogs are small animals. John is a frog. John is a small animal?', True],
  [51, 'Frogs are small animals. John is a frog. John is small?', True],
  [52, 'Frogs are small. John is a frog. John is small?', True],
  [53, 'Frogs are small. John is a frog. John is a small animal?', None],

  [54, 'John is a big mouse. John is big?', True],
  [55, 'John is a big mouse. John is a big mouse?', True],
  [56, 'John is a big mouse. John is a big thing?', None],

  [57, 'The car is red. The car is red?', True],
  [58, 'The car is red. The car is nice?', None],
  [59, ' The big mouse is strong. The mouse is a big mouse?', True],

# == NUMBER & PLURALITY ==

  # -- conjunction in have-objects --

  [60, 'Elephants have long trunks and short tails. John is an elephant. Who has a trunk and a tail?', 'John.'],
  [61, 'Elephants have long trunks and short tails. John is an elephant. Who has a long trunk and a short tail?', 'John.'],

  [62, 'Elephants have long trunks and no wings. John is an elephant. John has a wing?', False],
  [63, 'Elephants have long trunks and no wings. John is an elephant. John has no wing?', True],
  [64, 'Elephants have long trunks and no wings. John is an elephant. John does not have a wing?', True],
  [65, 'Elephants have long trunks and no wings. John is an elephant. Who does not have a wing?', ['John.', 'Elephants.']],
  [66, 'Elephants have long trunks and no wings. John is an elephant. John has a long trunk and no wing?', True],

  # -- disjunction in have-objects --

  [67, 'Elephants have trunks or tails. John is an elephant. John has no trunk. John has a tail?', True],
  [68, 'Elephants have either trunks or tails. John is an elephant. John has a tail and a trunk?', False],
  [69, 'Elephants have trunks or tails. John is an elephant. John has a tail or a trunk?', True],

  [70, 'Elephants have long or short trunks. John is an elephant. John does not have a long trunk. John has a short trunk?', True],
  [71, 'Elephants have long or short trunks. John is an elephant. John has a trunk?', True],
  [72, 'Elephants have long or short trunks. John is an elephant. John has a long trunk?', None],

# == COREFERENCE & ANAPHORA ==

  # -- basic property assertions --

  [73, 'John was yellow. John was yellow?', True],
  [74, 'John was yellow. John was nice?', None],
  [75, 'John was yellow. A man was nice?', None],

  [76, 'A man was yellow. A man was yellow?', True],
  [77, 'A man was yellow. A man was nice?', None],
  [78, 'A man was yellow. John was nice?', None],

  # -- definite descriptions --


  # -- definite description resolution --

  [79, 'An elephant was strong. An animal lifted a stone. Who lifted the stone?', ['The animal', 'The strong elephant', 'The elephant']],
  [80, 'An elephant was strong. The nice animal lifted a stone. Who lifted the stone?', ['The nice animal', 'The elephant.']],
  [81, 'An elephant was strong. The animal lifted a stone. Who lifted the stone?', 'The elephant'],
  [82, 'A nice elephant was strong. The nice animal lifted a stone. Who lifted the stone?', 'The nice elephant'],
  [83, 'A nice elephant was strong. A mouse was white. The white animal lifted the stone. Who lifted the stone?', 'The mouse'],
  [84, 'A nice elephant was strong. A flower was white. The animal lifted the stone. Who lifted the stone?', ['The nice elephant', 'The elephant.', 'The animal.']],
  [85, 'An old nice grey elephant was strong. The nice animal lifted a stone. Who lifted the stone?', ['The old nice grey elephant', 'The elephant.']],

  [86, 'A big old grey elephant was strong. The big animal lifted a stone. The stone was red. The old animal lifted a red stone?', True],
  [87, 'A big old grey elephant was strong. The big animal lifted a stone. The stone was heavy. The old animal lifted a heavy stone?', True],
  [88, 'A big old grey elephant was strong. The big animal lifted a stone. It was red. The grey animal lifted what?', ['The stone', 'A red stone.']],

  # -- determiners: a/the --


  # -- distinct indefinites --

  [89, 'A red car is big. A new car is small. A car is old?', None],
  [90, 'A red car is big. A new car is nice. Some car is red and big?', True],
  [91, 'A red car is big. A new car is nice. A car is red and nice?', None],
  [92, 'A red car is big. A new car is nice. The red car is big?', True],
  [93, 'A red car is big. A new car is nice. The new car is nice?', True],

  [94, 'A red car is big. The red car is strong. The car is red and strong?', True],
  [95, 'A red car is big. The car is strong. The car is red and strong?', True],
  [96, 'A red car is big. The car is strong. A car is black?', None],

  # -- pronoun resolution (he/she/it) --

  [97, 'Mary saw John. She was nice. Who was nice?', 'Mary'],
  [98, 'Mary saw John. He was nice. Who was nice?', 'John'],
  [99, 'John saw Mary. She was nice. Who was nice?', 'Mary'],
  [100, 'John saw Mary. He was nice. Who was nice?', 'John'],

  [101, 'A mother saw a man. She was nice. Who was nice?', ['The mother', 'The nice mother']],
  [102, 'A mother saw a man. He was nice. Who was nice?', ['The man', 'The nice man']],
  [103, 'A boy saw a girl. She was nice. Who was nice?', ['The girl', 'The nice girl']],
  [104, 'A boy saw a girl. He was nice. Who was nice?', ['The boy', 'The nice boy']],
  [105, 'A mother saw a fox. It was nice. Who was nice?', ['The fox', 'The nice fox']],
  [106, 'A mother saw a fox. She was nice. Who was nice?', ['The mother', 'The nice mother']],
  [107, 'A fox saw a mother. She was nice. Who was nice?', ['The mother', 'The fox.', 'The nice mother']],
  [108, 'A mother saw a fox. He was nice. Who was nice?', ['The fox', 'The nice fox']],
  [109, 'A fox saw a mother. He was nice. Who was nice?', ['The fox', 'The nice fox']],
  [110, 'A fox saw a mother. It was nice. Who was nice?', ['The fox', 'The mother.', 'The nice mother']],

  # -- names and non-names --

  [111, 'Muggles cannot disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?', False],
  [112, 'Muggles can not disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?', False],
  [113, 'Americans cannot disappear. Mr Dursley is an American. Mr Dursley can disappear?', False],
  [114, 'Americans can not disappear. Mr Dursley is an American. Mr Dursley can disappear?', False],
  [115, 'Catholics can not disappear. Mr Dursley is a catholic. Mr Dursley can disappear?', False],

  # -- true as adjective vs truth value --

  [116, 'Sue is a true patriot. Sue is a true patriot?', True],
  [117, 'Sue is a true patriot. Sue is a nice patriot?', None],
  [118, 'Sue is a true patriot. Sue is a true driver?', None],

  [119, 'The elephants saw a fox. They were nice. The elephants were nice?', True],
  [120, 'The elephants saw a fox. They were nice. The fox was nice?', None],
  [121, 'The elephants saw a fox. They were nice. Who were nice?', 'The elephants'],
  [122, 'The elephants saw a fox. It was nice.  The fox was nice?', True],
  [123, 'The elephants saw a fox. It was nice.  The elephants were nice?', None],

  [124, 'The fox saw the elephants. They were nice. The elephants were nice?', True],
  [125, 'The fox saw the elephants. They were nice. The fox was nice?', None],
  [126, 'The fox saw the elephants. It was nice.  The elephants were nice?', None],

  # -- she/he pronoun resolution --

  [127, 'Mary was in a room. She was in the room?', True],
  [128, 'Mary was in a room. She was in a room?', True],
  [129, 'Mary was in a room. She was not in the room?', False],
  [131, 'She was in a room. She was in the room?', True],

  [132, 'An apple was bad. She was in a room. She was in the room?', True],
  [133, 'An apple was bad and she was in a room. She was in the room?', True],
  [134, 'An apple was bad. She was in a room. An apple was in a room?', None],
  [135, 'An apple was bad and she was in a room. An apple was in a room?', None],

  [136, 'John was bad. She was in a room. John was in a room?', None],
  [137, 'She was in a room. Who was in the room?', 'She'],

  # -- these/they anaphora --

  [138, 'The aunts saw shoes. These were nice. What was nice?', 'The shoes'],
  [140, 'A car had a dent. This was deep. What was deep?', 'A dent'],
  [141, 'A car had a dent. It was fast. What was fast?', 'The car'],

  # -- definite/indefinite coreference --

  [142, 'A gray elephant was nice. A white elephant was nice. The elephant was cool. The white elephant was cool?', True],
  [143, 'A gray elephant was nice. A white elephant was nice. The elephant was cool. The gray elephant was cool?', None],
  [144, 'A gray elephant was nice. A white elephant was nice. It was cool. The white elephant was cool?', True],
  [145, 'A gray elephant was nice. A white elephant was nice. It was cool. The gray elephant was cool?', None],

  # -- pronouns, reflexives, reciprocals --


  [146, 'Mike ate berries in the forest bought by Mary. Mike ate berries in the forest bought by Mary?', True],
  [147, 'Mike ate berries in the forest bought by Mary. Mike ate berries in the forest bought by John?', None],
  [148, 'Bears ate berries in the forest bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  [149, 'Bears ate berries in the forest bought by Mary. Bears ate berries in the forest bought by John?', None],

  # -- reflexives --

  [150, 'John saw himself in the mirror. Who did John see?', ['John.', 'Himself.']],
  [151, 'John saw himself in the mirror. Did Mary see John in the mirror?', None],
  [152, 'The boy lost his backpack. Who does the backpack belong to?', 'The boy.'],
  [153, 'The boy lost his backpack. Did the boy find his backpack?', None],
  [154, 'The students brought their books. Whose books were they?', ["The students'.", 'The students.']],
  [155, 'John saw himself in the mirror. John saw John?', True],
  [156, 'John saw himself in the mirror. Did John see Mary?', None],
  [157, 'Mary blamed herself. Mary blamed Mary?', True],
  [158, 'Tom washed himself. Tom washed Tom?', True],
  [159, 'Tom washed himself. Did Tom wash Mary?', None],
  [160, 'Eve introduced herself. Eve introduced Eve?', True],

  # -- reciprocals --

  [161, 'John and Mary saw each other. John saw Mary?', True],
  [162, 'John and Mary saw each other. Mary saw John?', True],
  [163, 'John and Mary saw each other. Did John see Eve?', None],

  [164, 'Tom and Eve greeted each other. Tom greeted Eve?', True],
  [165, 'Tom and Eve greeted each other. Eve greeted Tom?', True],
  [166, 'Tom and Eve greeted each other. Did Tom greet Mary?', None],

  [167, 'The boys helped themselves. The boys helped the boys?', True],
  [168, 'The girls admired themselves. The girls admired the girls?', True],


# == POSSESSION & HAVE ==

  # -- basic have --

  [169, 'Elephants have trunks. Elephants have trunks?', True],
  [170, 'No elephant has wings. No elephant has wings?', True],

  [171, 'No elephants have wings. Some elephant has wings?', False],
  [172, 'Elephants have no wings. Some elephant has wings?', False],
  [173, 'Elephants have no wings. John has no wings?', None],

  # -- have with quantifiers and negation --

  [174, 'All elephants have no wings. Some elephant has wings?', False],
  [175, 'All elephants have no wings. John has no wings?', None],
  [176, 'Some elephants have no wings. Some elephant has wings?', None],
  [177, 'Some elephants have no wings. John has no wings?', None],
  [178, 'No elephants have wings. All elephants do not have wings?', True],

  [179, 'Elephants have trunks. John has a trunk?', None],
  [180, 'All elephants have trunks. John has a trunk?', None],
  [181, 'Some elephants have trunks. John has a trunk?', None],

  [182, 'Elephants have a trunk. Birds have a trunk?', None],
  [183, 'Elephants have a trunk. Birds do not have a trunk?', None],

  # -- have with adjective-modified objects --

  [184, 'Elephants have long trunks. John is an elephant. John has a trunk?', True],
  [185, 'Elephants have no trunks. John is an elephant. John has a trunk?', False],

  [186, 'Elephants have long grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  [187, 'Elephants have long and grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  [188, 'Elephants have long grey trunks. John is an elephant. Who has a grey trunk?', 'John.'],
  [189, 'Elephants have long and grey trunks. John is an elephant. Who has a grey trunk?', 'John.'],
  [190, 'Elephants have long grey trunks. John is an elephant. Who has a long red trunk?', None],

  [191, 'Elephants have no long red trunks. John is an elephant. John has a long red trunk?', False],
  [192, 'Elephants have no long red trunks. John is an elephant. John has a long trunk?', None],

  # -- have with negated adjectives --

  [193, ' Elephants have not red trunks. John is an elephant. John has a not red trunk?', True],
  [194, ' Elephants have not red trunks. John is an elephant. John has a trunk?', True],
  [195, ' Elephants have not red trunks. John is an elephant. John has a big trunk?', None],

  [196, ' Elephants have long not red trunks. John is an elephant. John has a long not red trunk?', True],
  [197, ' Elephants have long not red trunks. John is an elephant. John has a long trunk?', True],
  [198, ' Elephants have long not red trunks. John is an elephant. John has a long black trunk?', None],
  [199, ' Elephants have long not red trunks. John is an elephant. John has a not red trunk?', True],

  [200, ' Elephants have long not big trunks. John is an elephant. John has a long not big trunk?', True],
  [201, ' Elephants have long not big trunks. John is an elephant. John has a not big trunk?', True],
  [202, ' Elephants have long not red trunks. John is an elephant. John has a long not small trunk?', None],
  [203, ' Elephants have long not big trunks. John is an elephant. John has a long trunk?', True],

  # -- do not have --

  [204, 'Elephants do not have long red trunks. John is an elephant. John has a long red trunk?', False],
  [205, 'Elephants do not have wings. John is an elephant. John has wings?', False],
  [206, 'Elephants do not have wings. John is an elephant. John has a wing?', False],
  [207, 'Elephants do not have long red wings. John is an elephant. John has a wing?', None],
  [208, 'John has cars. John has cars?', True],
  [209, 'John has blue cars. John has a car?', True],
  [210, 'John has blue cars. John has a blue car?', True],
  [211, 'Animals have legs. Animal has a leg?', True],

  [212, 'Elephants have long trunks. John is an elephant. Who has a trunk?', 'John.'],

# == DEFINITE DESCRIPTIONS: X OF Y AND POSSESSIVES ==

  # -- X of Y in instrument phrases --

  [213, 'John ate berries with the edge of a spoon. John ate berries with the edge of a spoon?', True],
  [214, 'John ate berries with an edge of a spoon. John ate berries with an edge of a spoon?', True],
  [215, 'John ate berries with the edge of a spoon. John ate berries with the edge of a fork?', None],
  [216, 'John ate berries with the edge of a spoon. John ate berries with the tip of a spoon?', None],
  [217, 'John ate berries with an edge of a spoon. John ate berries with an edge?', True],
  [218, 'John ate berries with an edge of a spoon. John ate berries with a tip?', None],
  [219, 'John ate berries with an edge of a spoon. A spoon had an edge?', True],
  [220, 'John ate berries with an edge of a spoon. The spoon had the edge?', True],
  [221, 'John ate berries with the edge of the spoon. The spoon had the edge?', True],
  [222, 'John ate berries with the edge of the spoon. The spoon had the tip?', None],
  [223, 'John ate berries with the edge of a spoon. Berries have an edge?', None],

  # -- possessive 's constructions --

  [224, "John's brother has a car. John's brother has a car?", True],
  [225, "John's brother has a car. John's sister has a car?", None],
  [226, "Mary's sister owns a house. Who owns a house?", "Mary's sister."],
  [227, "John's brother's car is red. John's brother has a car?", True],
  [228, "John's brother's car is red. John's brother's car is blue?", False],
  [229, "Mary's uncle's bicycle is blue. Mary's uncle has a bicycle?", True],
  [230, "Mary's uncle's bicycle is blue. Mary's aunt has a bicycle?", None],

  # -- nested possessives --

  [231, "The roof of John's house is green. John has a house?", True],
  [232, "The handle of Mary's suitcase broke. Mary had a suitcase?", True],
  [233, "The handle of Mary's suitcase broke. Did the suitcase break?", None],

  # -- chained of-possessives --

  [234, 'The door of the house of John was open. John had a house?', True],
  [235, 'The door of the house of John was open. Was the door closed?', False],
  [236, 'The tail of the dog of Mary was short. Mary had a dog?', True],
  [237, "The color of John's car was black. John had a car?", True],
  [238, "The color of John's car was black. John had a truck?", None],
  [239, 'The owner of the horse of Mike smiled. Mike had a horse?', True],
  [240, 'The brother of the friend of Eve arrived. Eve had a friend?', True],
  [241, "The brother of the friend of Eve arrived. Did Eve's friend arrive?", None],
  [242, "John saw the mother of the boy. John saw a boy's mother?", True],
  [243, "John's sister laughed. Who has a sister?", 'John.'],
  [244, "John's sister laughed. Did John's brother laugh?", None],
  [245, "Mary's uncle arrived. Who has an uncle?", 'Mary.'],
  [246, 'The bicycle of Tom was new. Who had a bicycle?', 'Tom.'],
  [247, 'The bicycle of Tom was new. Was the bicycle old?', False],
  [248, 'The toy of the child was broken. Who had a toy?', ['The child.', 'A child.']],
  [249, 'The toy of the child was broken. Was the toy intact?', False],
  [250, 'John does not eat a carrot. John does not eat a carrot?', True],
  [251, 'John does not eat a carrot. John eats a carrot?', False],
  [252, 'John is not in a cave. John is not in a cave?', True],

# == POSSESSION INFERENCE FROM DESCRIPTIONS ==

  # -- the X of Y: property queries --

  [253, 'The head of Mary is clean. The head of Mary is clean?', True],
  [254, 'The head of Mary is clean. A head of Mary is clean?', True],
  [255, 'The head of Mary is clean. A head of Mike is clean?', None],
  [256, 'The head of Mary is clean. The head is clean?', True],

  [257, 'The car of Mary is clean. The car of Mike is clean?', None],

  [258, 'A leg of Mary is clean. A leg of Mary is clean?', True],
  [259, 'A leg of Mary is clean. A leg of Mary is long?', None],
  [260, 'A leg of Mary is clean. A leg of Mike is clean?', None],

  [261, "Mary's head is clean. Mary's head is clean?", True],
  [262, "Mary's head is clean. A head of Mary is clean?", True],
  [263, "Mary's head is clean. A head of Mike is clean?", None],
  [264, "Mary's head is clean. The head is clean?", True],

  [265, "Mary's leg is clean. A leg of Mary is clean?", True],
  [266, "Mary's leg is clean. A leg of Mary is long?", None],
  [267, "Mary's leg is clean. A leg of Mike is clean?", None],

  # -- possessive -> have inference --

  [268, "Mary's car is clean. Mary has a car?", True],
  [269, "Mary's car is clean. Mary has a clean car?", True],
  [270, "Mary's car is clean. Mary has a red car?", None],
  [271, "Mary's car is clean. Mary has a clean bike?", None],

  [272, "Elephant's head is green. John is an elephant. John has a head. John has a green head?", True],
  [273, 'The head of every elephant is green. John is an elephant. John has a green head?', True],
  [274, "Big elephant's head is green. John is an elephant. John has a head. John has a green head?", None],
  [275, 'A head of an elephant is green. An elephant has a green head?', True],

  [276, 'A head of an elephant is green. All elephants have a head. An elephant has a green head?', True],
  [277, 'A head of an elephant is green. Elephants have a head. An elephant has a green head?', True],

  # -- generic possessives --

  [279, "Elephant's head is green. Elephant's head is green?", 'Probably true'],
  [280, 'The head of Mary is clean. Mary has a clean head?', True],

  [281, 'The car of Mary is clean. Mary has a car?', True],
  [282, 'The car of Mary is clean. Mike has a car?', None],
  [283, 'The car of Mary is clean. Mary has a clean car?', True],
  [284, 'The car of Mary is clean. Mary has a red car?', None],
  [285, 'The car of Mary is clean. Mary has a clean bike?', None],

  # -- saw X of Y --

  [286, 'John saw the head of Mary. John saw the head of Mary?', True],
  [287, 'John saw the head of Mary. John saw a head of Mary?', True],
  [288, 'John saw the head of Mary. John saw the head of Mike?', None],
  [289, 'John saw the head of Mary. John saw a head?', True],
  [290, 'John saw the head of Mary. John saw the hands of Mary?', None],

  [291, 'John saw the car of Mary. Mary had a car?', True],

  [292, 'John saw the head of the elephant. John saw the head of the elephant?', True],
  [293, 'John saw the head of the elephant. John saw the head?', True],
  [294, 'John saw the head of the elephant. John saw a head?', True],
  [295, 'John saw the head of the elephant. John saw the tail of the elephant?', None],
  [296, 'John saw the head of the elephant. John saw a nice head?', None],
  [297, 'John saw a head of an elephant. John saw a head of an elephant?', True],
  [299, 'John saw a head of an elephant. John saw the head?', True],
  [300, 'John saw a head of an elephant. John saw a head?', True],
  [301, 'John saw a head of an elephant. John saw the tail of the elephant?', None],
  [302, 'John saw a head of an elephant. John saw a tail of an elephant?', None],
  [303, 'John saw a head of an elephant. John saw a nice head?', None],

  # -- saw possessive-'s --

  [304, "John saw Mary's head. John saw Mary's head?", True],
  [305, "John saw Mary's head. John saw a head of Mary?", True],
  [306, "John saw Mary's head. John saw Mike's head?", None],
  [307, "John saw Mary's head. John saw the head of Mike?", None],
  [308, "John saw Mary's head. John saw a head?", True],
  [309, "John saw Mary's head. John saw the hands of Mary?", None],

  [310, "John saw Mary's car. Mary had a car?", True],

  [311, "John saw Mary's clean car. Mary had a clean car?", True],
  [312, "John saw Mary's clean car. Mary had a red car?", None],
  [313, "John saw Mary's clean car. Mary had a clean bike?", None],

  # -- saw generic possessives --

  [314, "John saw elephant's head. John saw elephant's head?", True],
  [315, "John saw elephant's head. John saw the head?", True],
  [316, "John saw elephant's head. John saw a head of an elephant?", True],
  [317, "John saw elephant's head. John saw a head of a tiger?", None],
  [318, "John saw elephant's head. John saw a head?", True],
  [319, "John saw elephant's head. John saw the tail of the elephant?", None],
  [320, "John saw elephant's head. John saw a nice head?", None],

  # -- a-vs-the in of-phrases --

  [321, 'John saw a head of an elephant. John saw a head of the elephant?', True],
  [322, 'John saw a head of the elephant. John saw a head of the elephant?', True],
  [323, 'John saw a head of the elephant. John saw a head of an elephant?', True],
  [324, 'John saw a head of an elephant. John saw a head of the bear?', None],
  [325, 'John saw a head of an elephant. John saw a head of a bear?', None],
  [326, 'John saw a head of the elephant. John saw a head of the bear?', None],
  [327, 'John saw a head of the elephant. John saw a head of a bear?', None],
  [328, 'John saw a head of an elephant. John saw a tail of the elephant?', None],
  [329, 'John saw a head of the elephant. John saw a tail of the elephant?', None],
  [330, 'John saw a head of the elephant. John saw a tail of an elephant?', None],

  [331, 'John saw a twig of an elephant. The elephant had a twig?', True],
  [332, 'John saw a twig of an elephant. The elephant had a spoon?', None],
  [333, 'John saw a twig of an elephant. An elephant had a twig?', True],
  [334, 'John saw a twig of an elephant. An elephant had a spoon?', None],
  [335, 'John saw the twig of an elephant. The elephant had a twig?', True],

  # -- observation implies possession --

  [336, 'John saw the twig of an elephant. The elephant had the twig?', True],
  [337, 'John saw the twig of an elephant. The elephant had a spoon?', None],

  # -- colored X of colored Y --

  [338, 'John saw a blue head of a red elephant. John saw a blue head of a red elephant?', True],
  [339, 'John saw a blue head of a red elephant. John saw a blue head?', True],
  [340, 'John saw a blue head of a red elephant. John saw the blue head?', True],
  [341, 'John saw a blue head of a red elephant. John saw the head?', True],
  [342, 'John saw a blue head of a red elephant. John saw a blue tail?', None],
  [343, 'John saw a blue head of a red elephant. John saw a head of an elephant?', True],
  [344, 'John saw a blue head of a red elephant. John saw a head of the red elephant?', True],

  # -- of-phrases in event descriptions --

  [345, 'The hand of a man moved a wheel. The hand of a man moved a wheel?', True],
  [346, 'The hand of a man moved a wheel. The man had a hand?', True],
  [347, 'The hand of a man moved a wheel. A man had a hand?', True],
  [348, 'The hand of a man moved a wheel. A man had a wheel?', None],

  # -- complex of-chains in events --

  [349, 'A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand of a man moved a wheel of a large wheelbarrow?', True],
  [350, 'A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand of an elephant moved a wheel of a large wheelbarrow?', None],
  [351, 'The blue hand of a man moved a wheel of the large wheelbarrow. A blue hand of a man moved a wheel of a large wheelbarrow?', True],
  [352, 'The blue hand of a man moved the wheel of the large wheelbarrow. The blue hand of a man moved the wheel of the large wheelbarrow?', True],
  [353, 'The blue hand of a man moved the wheel of the large wheelbarrow. The blue hand of a man moved the large wheelbarrow?', None],
  [354, 'A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel?', True],
  [355, 'A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheelbarrow?', None],
  [356, 'A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand moved a wheel?', True],
  [357, 'A blue hand of a man moved a wheel of a large wheelbarrow. A right hand moved a wheel?', None],
  [358, 'A blue hand of a man moved a wheel of a large wheelbarrow. A leg moved a wheel?', None],
  [359, 'A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel of a small wheelbarrow?', None],
  [360, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a hand?', True],
  [361, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a blue hand?', True],
  [362, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a red hand?', None],
  [363, 'A blue hand of a man moved a wheel of a large wheelbarrow. The man had a wheel?', None],
  [364, 'A blue hand of a man moved a wheel of a large wheelbarrow. The wheelbarrow had a wheel?', True],
  [365, 'A blue hand of a man moved a wheel of a large wheelbarrow. A large wheelbarrow had the wheel?', True],
  [366, 'A blue hand of a man moved a wheel of a large wheelbarrow. The large wheelbarrow had a wheel?', True],
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

  [467, 'The red car has the price two dollars. The blue car costs three dollars. The green car costs 2 dollars. The red car costs as much as the green car?', True],

  # -- length comparisons --

  [468, 'The length of the red car is three meters. The blue car is 2 meters long. The red car has the same length as the blue car?', False],
  [469, 'The length of the red car is three meters. The blue car is 2 meters long. The red car does not have the same length as the blue car?', True],
  [470, 'The length of the red car is three meters. The blue car is 3 meters long. The red car has the same length as the blue car?', True],
  [471, 'The length of the red car is three meters. The blue car is 3 meters long. The red car does not have the same length as the blue car?', False],

  [472, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is more than the length of the black car?""", False],
  [473, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is less than the length of the black car?""", True],
  [474, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is less than 2 meters?""", False],
  [475, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is over 2 meters?""", True],
  [476, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is more than 2 meters?""", True],
  [477, """The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is under 4 meters?""", True],

  [478, 'The length of the car is 3 meters. The bike has the same length as the car. The length of the bike is 3 meters?', True],

  # -- same-as measure equality --

  [479, 'The price of the car is 3 dollars. The bike has the same price as the car.  The price of the bike is 3 dollars?', True],

  [480, 'The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 3 dollars?', True],
  [481, 'The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 2 dollars?', False],
  [482, 'The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 3 drahms?', False],

  # -- as-much-as measure equality --

  [483, 'The price of the car is 3 dollars. The bike costs as much as the car. The bike costs 3 dollars?', True],
  [484, 'The price of the car is 3 dollars. The bike costs as much as the car. The price of the bike is less than 20 dollars?', True],
  [485, 'The price of the car is 3 dollars. The bike costs as much as the car. The price of the bike is more than 20 dollars?', False],
  [486, 'The price of the car is 3 dollars. The bike costs as much as the car. The bike costs less than 20 dollars?', True],
  [487, 'The price of the car is 3 dollars. The bike costs as much as the car. The bike costs more than 20 dollars?', False],

  [488, 'The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs less than 20 tons?', True],
  [489, 'The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs more than 2 tons?', True],
  [490, 'The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs more than 20 tons?', False],

  # -- what-questions on measures --

  [491, "Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What is 80 kilometers long?", 'Nile'],
  [492, "Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What has the length 20 kilometers?", 'Amazon'],

  [493, "Car's length is 80 kilometers. Bike's length is 10 kilometers. What is 80 kilometers long?", 'A car'],
  [494, "Car's length is 80 kilometers. Bike's length is 10 kilometers. What has the length 10 kilometers?", 'A bike'],
  [495, "The car's length is 80 kilometers. The bike's length is 10 kilometers. What is 80 kilometers long?", 'The car'],
  [496, "The car's length is 80 kilometers. The bike's length is 10 kilometers. What has the length 10 kilometers?", 'The bike'],

  [497, "Emajogi's length is 80 kilometers. What is 80 kilometers long?", 'Emajogi'],
  [498, "Emajogi's length is 80 kilometers. What is 200 kilometers long?", None],
  [499, 'The length of Nile is 10 meters. What has the length 10 meters?', 'Nile'],

  # -- what-is-N-long questions --

  [500, 'Nile is 10 meters long. What is 10 meters long?', 'Nile'],
  [501, 'Nile is 10 meters long. Emajogi is 20 meters long. The nice river is 100 meters long. What is 100 meters long?', 'The nice river'],
  [502, 'The red straw is 10 meters long. The blue straw is 5 meters long. What is 5 meters long?', 'The blue straw'],
  [503, 'The red straw is 10 meters long. The blue straw is 5 meters long. What is 10 meters long?', 'The red straw'],

  [504, 'The red car has the price two dollars. The blue car costs three dollars. What costs 3 dollars?', 'The blue car'],
  [505, 'The red car has the price two dollars. The blue car costs three dollars. What has the price 2 dollars?', 'The red car'],
  [506, 'The red car has the price two dollars. The blue car costs three dollars. What has the price 3 dollars?', 'The blue car'],

  [507, 'The bicycle repaired by Mike was expensive. Mike repaired the bicycle?', True],
  [508, 'The bicycle repaired by Mike was expensive. The bicycle was expensive?', True],
  [509, 'The bicycle repaired by Mike was expensive. The bicycle was cheap?', False],

# == QUANTIFIERS: UNIVERSAL & EXISTENTIAL ==

  # -- all implies bare plural --

  [510, 'All elephants are animals. Elephants are animals?', True],
  [511, 'All elephants are animals. Some elephant is an animal?', True],
  [512, 'All elephants are animals. All elephants are animals?', 'True'],
  [513, 'All elephants are animals. John is an animal?', None],
  [514, 'All elephants are animals. Elephants are not animals?', False],
  [515, 'All elephants are animals. Some elephants are not animals?', False],
  [516, 'All elephants are animals. All elephants are not animals?', False],

  # -- some: existential --

  [517, 'Some elephants are animals. Elephants are animals?', None],
  [518, 'Some elephants are animals. Some elephant is an animal?', True],
  [519, 'Some elephants are animals. All elephants are animals?', None],
  [520, 'Some elephants are animals. John is an animal?', None],
  [521, 'Some elephants are animals. Elephants are not animals?', False],
  [522, 'Some elephants are animals. Some elephants are not animals?', None],
  [523, 'Some elephants are animals. All elephants are not animals?', False],
  [524, 'Some elephants are not animals. All elephants are animals?', False],

  # -- all-not vs not-all --


  [526, 'No elephant is an animal. No elephant is an animal?', True],
  [527, 'No elephant is an animal. Some elephant is an animal?', False],

  # -- all in object position --

  [528, 'John likes all boxers. Mike is a boxer. John likes Mike?', True],
  [529, 'Bears eat all boxers. Mike is a boxer. Greg is a bear. Greg eats Mike?', True],
  [530, 'Bears eat most boxers. Mike is a boxer. Greg is a bear. Bears eats Mike?', 'Probably true.'],
  [531, 'Bears eat most boxers. Mike is a boxer. Greg is a bear. Bears eats Greg?', None],
  [532, 'Bears eat all boxers. Mike is a boxer. Bears eat boxers?', True],
  [533, 'Bears eat some boxers. Mike is a boxer. Bears eat Mike?', None],
  [534, 'John likes some boxers. Mike is a boxer. John likes Mike?', None],

  [535, 'Elephants are animals. Some elephant is an animal?', True],
  [536, 'Elephants are animals. All elephants are animals?', True],
  [537, 'Elephants are animals. John is an animal?', None],
  [538, 'Elephants are animals. Elephants are not animals?', False],
  [539, 'Elephants are animals. Some elephants are not animals?', False],
  [540, 'Elephants are animals. All elephants are not animals?', False],

# == QUANTIFIERS: PROPORTIONAL & NUMERIC ==

  # -- distinct indefinites with quantifiers --

  [541, 'The red square has a nail. A blue square has a hole. A square has a nail?', True],
  [542, 'The red square has a nail. A blue square has a hole. A square has a hole?', True],
  [543, 'The red square has a nail. A blue square has a hole. A square has a dot?', None],
  [544, 'The red square has a nail. A blue square has a hole. A red square has a nail?', True],
  [545, 'The red square has a nail. A blue square has a hole. A blue square has a hole?', True],
  [546, 'The red square has a nail. A blue square has a hole. A red square has a hole?', None],

  [547, 'The red square is nice. A blue square is cool. Some square is cool?', True],
  [548, 'The red square is nice. A blue square is cool. There is a nice square?', True],
  [549, 'The red square is nice. A blue square is cool. A square is empty?', None],

  [550, 'Most bears are big. John is a bear. John is big?', 'Likely true.'],

# == COMPARATIVES & EQUALITY ==

  # -- basic comparatives --

  [551, 'John is nicer than Mike. Mike is nicer than Eve. Who is nicer than Eve?', ['John and Mike.', 'John.', 'Mike.']],
  [552, 'John is nicer than Mike. Mike is nicer than Eve. Who is nicer than John?', None],
  [553, 'The red car is faster than the blue car. Is the blue car faster than the red car?', False],
  [554, 'The red car is faster than the blue car. Is the green car faster than the red car?', None],

  # -- equality comparisons --

  [555, 'John is as tall as Bill. Is John taller than Bill?', False],
  [556, "John is as tall as Bill. Is John's height equal to Bill's?", True],

  # -- which-questions on comparatives --

  [558, 'The mountain is higher than the hill. Is the hill higher than the mountain?', False],
  [559, "This book is more interesting than that one. Is 'that one' more interesting?", False],

# == COORDINATION (NP, VP, CLAUSAL) ==

  # -- NP coordination with lists --

  [560, 'Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a toy?', True],
  [561, 'Elephants, foxes and rabbits are nice animals and good toys. John is a fox. John is a good toy?', True],
  [562, 'Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal?', True],
  [563, 'Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal and a toy?', True],
  [564, 'Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal or a toy?', True],

  [565, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a bird?', False],
  [566, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is not a bird?', True],
  [567, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a small fish?', False],
  [568, 'Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a fish?', None],

  [569, 'Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a red toy?', None],

  # -- either-or coordination --

  [570, 'Elephants and sparrows are either animals or birds. John is a sparrow. John is a bird. John is an animal?', False],
  [571, 'Elephants and sparrows are either animals or birds. John is a sparrow. Sparrows are birds. John is not an animal?', True],
  [572, 'Elephants and sparrows are animals or birds. John is a sparrow. John is a bird. John is an animal or a bird?', True],
  [573, 'Elephants and sparrows are animals or birds. John is a sparrow. John is a bird. John is an elephant?', None],
  [574, 'Elephants or sparrows are animals. John is an elephant. Sparrows are not animals. John is an animal?', True],

  # -- class independence --

  [575, 'Elephants are animals. Birds are animals?', None],
  [577, 'Elephants are animals. Birds are nice animals?', None],

  [579, 'John saw the blue head of the red elephant. John saw the blue head of the red elephant?', True],
  [580, 'John saw the blue head of the red elephant. John saw the red head of the blue elephant?', None],

# == LISTS AND CONJUNCTIONS ==

  # -- conjunction of class properties --

  [581, 'Cars are nice. Cars have brakes. Cars are nice and have brakes?', True],
  [582, 'Cars are nice. Cars are nice and have brakes?', None],
  [583, 'Cars have brakes. Cars are nice and have brakes?', None],
  [584, 'Cars are nice and cool and have brakes. Cars are nice and cool and have brakes?', True],
  [585, 'Cars are nice and cool and have brakes. Cars have brakes and are nice and cool?', True],
  [586, 'Cars are cool and have brakes. Cars are nice and cool and have brakes?', None],
  [587, 'Cars are nice and cool. Cars have brakes and are nice and cool?', None],
  [588, 'Cars have fenders. Cars have brakes. Cars have brakes and fenders?', True],
  [589, 'Cars have fenders. Cars have brakes and fenders?', None],
  [590, 'Cars have brakes. Cars have brakes and fenders?', None],

  # -- NP conjunction as subject --

  [591, 'John and Mary saw the movie. Did Mary see the movie?', True],
  [592, 'John and Mary saw the movie. Did Mary see a play?', None],
  [593, 'John and Mary saw the movie. Who saw the movie?', 'John and Mary.'],

  # -- conjoined adjectives --

  [594, 'A tall and quiet man entered. A man entered?', True],
  [595, 'A tall and quiet man entered. A woman entered?', None],
  [596, 'A tall and quiet man entered. The man was tall?', True],
  [597, 'A tall and quiet man entered. The man was quiet?', True],
  [598, 'A tall and quiet man entered. The man was short?', False],

  [599, 'A red and blue flag waved. The flag was red?', True],
  [600, 'A red and blue flag waved. The flag was blue?', True],

  # -- conjoined objects --

  [601, 'John bought a red car and a blue bicycle. John bought a car?', True],
  [602, 'John bought a red car and a blue bicycle. John bought a bicycle?', True],
  [603, 'John bought a red car and a blue bicycle. Did John buy a truck?', None],
  [604, 'John bought a red car and a blue bicycle. The car was red?', True],
  [605, 'John bought a red car and a blue bicycle. The bicycle was blue?', True],
  [606, 'John bought a red car and a blue bicycle. The car was blue?', False],

  # -- VP conjunction --

  [607, 'The cat sat on the mat and purred. Did the cat purr?', True],
  [608, 'The cat sat on the mat and purred. Did the cat bark?', None],

  # -- conjoined VPs with different objects --

  [609, 'John ate an apple and drank some water. What did John drink?', ['Water.', 'Some water.']],
  [610, 'John ate an apple and drank some water. Did John eat a banana?', None],
  [611, 'The students studied hard and passed the exam. Did the students pass the exam?', True],
  [612, 'The students studied hard and passed the exam. Did the students fail the exam?', False],

  # -- conjoined verbs, shared object --

  [614, 'Mary washed and dried the cup. Mary washed the cup?', True],
  [615, 'Mary washed and dried the cup. Mary dried the cup?', True],
  [616, 'Mary washed and dried the cup. Did Mary break the cup?', None],

  [617, 'Tom opened the door and the window. Tom opened the door?', True],
  [618, 'Tom opened the door and the window. Tom opened the window?', True],
  [619, 'Tom opened the door and the window. Tom did not open the door?', False],

  [620, 'John bought a red car and a blue bicycle. What did John buy?', 'A red car and a blue bicycle'],
  [621, 'Tom opened the door and the window. What did Tom open?', 'The door and the window'],
  [622, 'Mary washed and dried the cup. Did Mary iron the cup?', None],

  # -- conjunction with can --

  [623, 'John and Eve can swim. Mark and John are animals. Who can swim and is an animal?', 'John'],
  [624, 'John and Eve can swim. Mark and John are animals. Who is an animal and can swim?', 'John'],
  [625, 'John and Eve can swim. Mark is an animal. Who can swim and is an animal?', None],

  # -- either-or --

  [626, 'Either John or Bill went to the store. Did someone go to the store?', True],
  [627, 'Either John or Bill went to the store. Did Mary go to the store?', None],

  # -- class defaults --

  [628, 'Cars are nice. Cars are nice?', True],

  # -- subclass exceptions --

  [629, 'Red cars are not nice. Cars are nice. Cars are nice?', True],
  [630, 'Red cars are not nice. Cars are nice. Red cars are nice?', False],
  [631, 'Red cars are not nice. Cars are nice. Blue cars are nice?', True],

  [632, 'Penguins happily live in water. Penguins happily live in water?', True],
  [633, 'Penguins happily live in cold water. Penguins happily live in cold water?', True],

# == INTERNAL MODIFICATION ==


  # -- basic appositive --

  [634, 'John, a doctor, arrived. John is a doctor?', True],
  [635, 'John, a doctor, arrived. John is a nurse?', None],
  [636, 'Mary, a pilot, smiled. Who is a pilot?', 'Mary.'],
  [637, 'Paul, a carpenter, carried a box. Paul carried a box?', True],
  [638, 'Paul, a carpenter, carried a box. Paul is a plumber?', None],

  [640, 'The manager, Anna, called Eve. Anna is the manager?', True],

  [641, 'John, my neighbor, owns a bicycle. John owns a bicycle?', True],
  [642, 'My neighbor, John, owns a bicycle. Who is my neighbor?', 'John.'],
  [643, 'Dr. Smith, a surgeon, entered the room. Dr. Smith is a surgeon?', True],
  [644, 'Dr. Smith, a surgeon, entered the room. Dr. Smith is a dentist?', None],

  [645, 'Tom, a friend of Mary, laughed. Tom is a friend of Mary?', True],
  [646, 'Tom, a friend of Mary, laughed. Mary is a friend of Tom?', None],
  [647, 'Tom, a friend of Mary, laughed. Tom is a friend of Eve?', None],

  [648, 'Sara, the sister of Mike, left. Sara is the sister of Mike?', True],
  [649, 'Sara, the sister of Mike, left. Sara is the brother of Mike?', False],

  # -- noun-noun compounds --

  [650, 'A school bus arrived. A bus arrived?', True],
  [651, 'A school bus arrived. A truck arrived?', None],
  [652, 'A chocolate cake fell. A cake fell?', True],
  [653, 'A chocolate cake fell. A pie fell?', None],
  [654, 'A stone wall collapsed. A wall collapsed?', True],
  [655, 'A kitchen door was open. A door was open?', True],

  # -- adjective from noun modifier --

  [656, 'A village road was narrow. A road was narrow?', True],
  [657, 'A coffee cup broke. A cup broke?', True],
  [658, 'A coffee cup broke. A plate broke?', None],
  [659, 'A garden wall was high. Some wall was high?', True],
  [660, 'A garden wall was high. A wall was low?', None],

  # -- present participial modifier --

  [661, 'The man carrying a bag waved. The man carried a bag?', True],
  [662, 'The man carrying a bag waved. The man carried a box?', None],

  # -- holding as participial --

  [663, 'The woman holding a lamp sang. The woman held a lamp?', True],
  [664, 'The child wearing a hat ran. The child wore a hat?', True],
  [665, 'The child wearing a hat ran. The child wore a coat?', None],

  # -- containing as participial --

  [666, 'The box containing apples fell. The box contained apples?', True],
  [667, 'The box containing apples fell. The box contained oranges?', None],

  # -- standing as participial --

  [668, 'The man standing by the door coughed. The man stood by the door?', True],
  [669, 'The man standing by the door coughed. The man stood by the window?', None],

  # -- parked as participial --

  [670, 'The car parked behind the house was blue. The car was behind the house?', True],
  [671, 'The car parked behind the house was blue. The car was in front of the house?', False],
  [672, 'The children playing in the garden laughed. The children were in the garden?', True],
  [673, 'The cup filled with water fell. The cup contained water?', True],
  [674, 'The road leading to the village was narrow. The road led to the village?', True],
  [675, 'The road leading to the village was narrow. The road was wide?', False],
  [676, 'The tree growing near the river was tall. The tree grew near the river?', True],

  # -- participial with modified object --

  [677, 'The man carrying a red bag waved. The bag was red?', True],
  [678, 'The man carrying a red bag waved. The bag was blue?', False],
  [679, 'The woman holding a heavy lamp sang. The lamp was heavy?', True],
  [680, 'The woman holding a heavy lamp sang. The lamp was light?', False],
  [681, 'The child wearing a small hat ran. The hat was small?', True],
  [682, 'The letter written by Mary was long. Mary wrote a long letter?', True],
  [683, 'The letter written by Mary was long. The letter was short?', False],
  [684, 'The cake baked by John was sweet. John baked a sweet cake?', True],
  [685, 'The dog chased by the boy was black. The boy chased a black dog?', True],
  [686, 'The dog chased by the boy was black. The dog was white?', False],

  # -- past participial modifier --

  [687, 'The letter written by Mary arrived. Mary wrote the letter?', True],
  [688, 'The cake baked by John was sweet. John baked the cake?', True],
  [689, 'The cake baked by John was sweet. The cake was bitter?', False],
  [690, 'The song sung by Eve was sad. Eve sang the song?', True],

  # -- passive participial --

  [691, 'The dog chased by the boy escaped. The boy chased the dog?', True],
  [692, 'The dog chased by the boy escaped. Did the dog catch the boy?', None],
  [693, 'The woman admired by John smiled. John admired the woman?', True],

  [694, 'The doctor who treated Mary called John. The doctor treated Mary?', True],
  [695, 'The doctor who treated Mary called John. The doctor called John?', True],
  [696, 'The doctor who treated Mary called John. Did the doctor treat John?', None],

  [697, 'The painter who lived in Rome sold a picture. The painter lived in Rome?', True],
  [698, 'The painter who lived in Rome sold a picture. The painter sold a picture?', True],
  [699, 'The painter who lived in Rome sold a picture. Did the painter live in Paris?', None],

  [700, "John's friend from Paris bought a camera. John had a friend?", True],
  [701, "John's friend from Paris bought a camera. The friend was from Paris?", True],
  [702, "John's friend from Paris bought a camera. Was the friend from London?", None],

  [703, "Mary's brother carrying a box entered. Mary had a brother?", True],
  [704, "Mary's brother carrying a box entered. The brother carried a box?", True],
  [705, "Mary's brother carrying a box entered. Did the brother carry a bag?", None],

  [706, 'The student carrying the books greeted the teacher. The student carried the books?', True],
  [707, 'The student carrying the books greeted the teacher. The student greeted the teacher?', True],
  [708, 'The student carrying the books greeted the teacher. Did the student greet the principal?', None],

  [709, 'The letter was written in June. Was the letter written?', True],
  [710, 'Bears ate berries in a forest. Bears did not eat berries in a forest?', False],
  [711, 'Bears ate berries in a forest. Bears did not eat berries in a field?', None],

# == RELATIVE CLAUSES ==

  # -- who-clauses in rules --

  [712, 'Big bears who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', True],
  [713, 'Big bears who have a trunk have a tail. John is a big bear. John has a nose. John has a tail?', None],
  [714, 'Big bears who have a trunk have a tail. John is a bear. John has a trunk. John has a tail?', None],

  [715, 'Big bears who are nice and have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', None],
  [716, 'Big bears who are nice and have a trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', True],
  [717, 'Big bears who are nice and who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', None],
  [718, 'Big bears who are nice and who have a trunk have a tail. John is a big bear. John is nice. John has a tail?', None],
  [719, 'Big bears who are nice and who have a trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', True],

  [720, 'Bears who are nice and have a long trunk have a tail. John is a nice big bear. John has a long trunk. John has a tail?', True],
  [721, 'Bears who are nice and have a long trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', None],
  [722, 'Bears who have a trunk are nice. John is a bear. John has a trunk. John is nice?', True],
  [723, 'Bears who have a trunk are nice. John is a bear. John has a nose. John is nice?', None],

  [724, 'Bears who are nice and eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?', True],
  [725, 'Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?', True],
  [726, 'Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats fish. John has a tail?', None],

  # -- simple who-clauses --

  [727, 'Bears who are big are strong. John is a big nice bear. John is strong?', True],
  [728, 'Bears who are big are strong. John is a bear. John is strong?', None],
  [729, 'Bears who have tails are strong. John is a big nice bear. John has a tail. John is strong?', True],
  [730, 'Bears who have tails are strong. John is a big nice bear.  John is strong?', None],
  [731, 'Bears who eat fish are strong. John eats fish. John is a bear. John is strong?', True],
  [732, 'Bears who eat fish are strong. John is a bear. John is strong?', None],
  [733, 'Bears who eat fish are strong. John eats carrots. John is a bear. John is strong?', None],
  [734, 'Nice bears who have tails are strong. John is a nice bear. John has a tail. John is strong?', True],
  [735, 'Nice bears who have tails are strong. John is a bear. John has a tail. John is strong?', None],
  [736, 'Nice bears who have tails are strong. John is a nice bear. John has a head. John is strong?', None],

  # -- who-clauses with pre-modifier --

  [737, 'Nice bears who are big are strong. John is a big nice bear. John is strong?', True],
  [738, 'Nice bears who are big are strong. John is a nice bear. John is strong?', None],
  [739, 'Nice bears who eat fish are strong. John is a nice bear. John eats fish. John is strong?', True],

  [740, 'Nice bears who eat big fish are strong. John is a nice bear. John eats big fish. John is strong?', True],
  [741, 'Nice bears who eat big fish are strong. John is a nice bear. John eats big carrots. John is strong?', None],
  [742, 'Nice bears who eat big fish are strong. John is a nice bear. John eats fish. John is strong?', None],

  # -- the-definite with who-clause --

  [743, 'The bear who is big is strong. The bear is strong?', True],
  [744, 'The bear who is big is strong. The big bear is strong?', True],
  [745, 'The bear who is big is strong. The big bear is white?', None],
  [746, 'The bear who is big is strong. Who is strong?', ['The big bear', 'The bear who is big.', 'The bear.']],

  [747, 'The bear who is big eats fish. The bear who is big eats fish?', True],
  [748, 'The bear who is white eats fish. The bear who is white eats fish?', True],

  [749, 'The bear who was white ate a fish. The bear who was white ate a fish?', True],
  [750, 'The bear who was white ate a fish. The bear ate a fish?', True],
  [751, 'The bear who was white ate a fish. The white bear ate a fish?', True],

  [752, 'Bears who were nice ate. Nice bears ate?', True],
  [753, 'The bear who was nice ate. The bear ate?', True],

  [754, 'Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat fish?', True],
  [755, 'Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat tables?', None],
  [756, 'Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat fish who are strong?', [True, 'Likely true']],
  [757, 'Bears who are nice eat fish who are strong. John is a nice bear. Nice bears eat strong fish?', [True, 'Likely true']],

  # -- past-tense who-clauses --

  [758, 'The bear who was nice ate the fish who was strong. The bear who was nice ate the fish who was strong?', True],
  [759, 'The bear who was nice ate the fish who was strong. The nice bear ate the strong fish?', True],
  [760, 'The bear who was nice ate the fish who was strong. The bear who was nice ate the fish who was white?', None],

  [761, 'The bear who was nice and white ate the fish who was big. The nice bear ate the big fish?', True],

  # -- conjoined who-clauses --

  [762, 'The bear who was white and ate a fish was cool. The white bear who ate a fish was cool?', True],
  [763, 'The bear who was white and ate a fish was cool. The bear who ate a fish was cool?', True],
  [764, 'The bear who was white and ate a fish was cool. The white bear who ate a fish was strong?', None],
  [765, 'The bear who was white and ate a fish was cool. The black bear who ate a fish was cool?', None],

  [766, 'The bear who was white and ate a big fish was cool. The white bear who ate a big fish was cool? ', True],
  [767, 'The bear who was white and ate a big fish was cool. The white bear who ate a fish was cool? ', True],
  [768, 'The bear who was white and ate a big fish was cool. The white bear who ate a strong fish was cool? ', None],

  [769, 'The nice bear who was white and ate a big fish was cool. The white nice bear who ate a big fish was cool? ', True],
  [770, 'The nice bear who was white and ate a big fish also ate berries. The white nice bear who ate a big fish also ate berries? ', True],
  [771, 'The nice bear who was white and ate a big fish also ate blue berries. The white nice bear who ate a big fish also ate blue berries? ', True],
  [772, 'The nice bear who was white and ate a big fish also ate blue berries. The white nice bear who ate a big fish also ate berries? ', True],
  [773, 'The nice bear who was white and ate a big fish also ate blue berries. The bear ate berries? ', True],
  [774, 'The nice bear who was white and ate a big fish also ate blue berries. The bear ate bread? ', None],

  [775, 'The bear who ate a big fish ate blue berries. The bear who ate a fish also ate blue berries?', True],
  [776, 'The bear who ate a big fish ate blue berries. The bear who ate a fish ate big berries?', None],
  [777, 'The bear who ate a big fish ate blue berries. John is big?', None],
  [778, 'The bear who ate a big fish ate blue berries. John is blue?', None],
  [779, 'The bear who ate a big fish ate blue berries. John is a fish?', None],

  # -- conjoined verbs in who-clause --

  [780, 'The woman who sang and danced smiled. The woman sang?', True],
  [781, 'The woman who sang and danced smiled. The woman danced?', True],
  [782, 'The woman who sang and danced smiled. The woman did not sing?', False],

  [783, 'The boy with a red hat and a blue coat ran. The boy had a red hat?', True],
  [784, 'The boy with a red hat and a blue coat ran. The boy had a blue coat?', True],

  # -- who-clause on object --

  [785, 'Bears eat fish who are strong. John is a bear. John eats strong fish?', True],
  [786, 'Bears eat fish who are strong. John is a fox. John eats strong fish?', None],
  [787, 'Bears eat fish who are strong. John is a bear. John eats red fish?', None],

  [788, 'Bears eat red fish who are strong. John is a bear. John eats red strong fish?', True],
  [789, 'Bears eat red fish who are strong. John is a bear. John eats yellow strong fish?', None],
  [790, 'Bears eat red fish who are strong. John is a bear. John eats yellow fish?', None],

  # -- subject and object who-clauses --

  [791, 'Bears who are nice eat fish who are strong. John is a nice bear. John eats strong fish?', True],
  [792, 'Bears who are nice eat fish who are strong. John is a bear. John eats strong fish?', None],
  [793, 'Bears who are nice eat fish who are strong. John is a nice bear. John eats yellow fish?', None],

  [794, 'Bears who are nice and white eat fish who are strong and red. John is a nice white bear. John eats red strong fish?', True],
  [795, 'Bears who are nice and white eat fish who are strong and red. John is a nice bear. John eats red strong fish?', None],
  [796, 'Bears who are nice and white eat fish who are strong and red. John is a nice white bear. John eats yellow strong fish?', None],

  # -- which-clauses on objects --

  [797, 'A man liked a car which a woman bought. The car was red. The man liked the car which a woman bought?', True],
  [798, 'A man liked a car which a woman bought. The car was red. The man liked the red car which a woman bought?', True],
  [799, 'A man liked a car which a woman bought. The car was red. The man liked a car which a boy bought?', None],
  [800, 'A man liked a car which a woman bought. The car was red. A man liked a red car which a woman bought?', True],
  [801, 'A man liked a car which a woman bought. The car was red. The man did not like the red car which the woman bought?', False],
  [802, 'A man liked a car which a woman bought. The car was red. The man did not like the red car which a woman bought?', False],

  # -- which-clause with pronoun --

  [803, 'A man liked a car which he bought. The car was red. The man bought the red car?', True],
  [804, 'A man liked a car which he bought. The car was red. A man bought a red car?', True],

  # -- which-clause adding properties --

  [805, 'John has a red car which is nice and big. The nice car is big and red?', True],
  [808, 'Bears ate berries in a forest which was bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  [809, 'Bears ate berries in a forest which was seen by Mary. Bears ate berries in the forest seen by Mary?', True],
  [810, 'Bears ate berries in a forest which was bought by Mike. Bears ate berries in the forest bought by Mike?', True],
  [811, 'Bears ate berries in a forest which was bought by Mary. Bears ate berries in the forest bought by John?', None],
  [812, 'John lives in a red car bought by Mary. Mary bought the car?', True],

  [813, 'Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest which was bought by Mary?', True],
  [814, 'Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest which was bought by John?', None],
  [815, 'Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest bought by Mary?', True],

  [816, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by Mary?', True],
  [817, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by John?', None],
  [818, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  [819, 'Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by John?', None],

  [820, 'A man had a car which a woman bought. The car was red. Who had a red car?', ['The man', 'The man and the woman.', 'The woman.']],

  # -- which-clause on location --

  [821, 'Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest which was bought by her?', True],
  [822, 'Bears ate nice berries in a big forest which was seen by Mary. Bears ate berries in the forest which was seen by her?', True],
  [823, 'Bears ate nice berries in a big forest which was bought by Mike. Bears ate berries in the forest which was bought by him?', True],
  [824, 'Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest which was bought by a man?', None],
  [825, 'Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest?', True],

  [826, 'Bears ate berries in the forest which was bought by Mary. The forest was bought by Mary?', True],

  # -- which-clause on location object --

  [827, 'John lives in a car which is red. The car is red?', True],
  [828, 'John lives in a car which is red. The car is nice?', None],
  [829, 'John lives in a car which is red. John lives in a red car?', True],
  [830, 'John lives in a car which is red. John lives in a nice car?', None],

  [831, 'John lives in a car which is red and was bought by Mary. The nice car was bought by Mary?', None],

  [832, 'John has a car which is nice and red. The car is red and nice?', True],
  [833, 'John has a car which is nice and red. The red car is nice?', True],
  [834, 'John has a car which is nice and red. The big car is nice?', None],

  # -- named entities in which-clauses --

  [835, 'John had a car which Eve bought. John had a car which Eve bought?', True],
  [836, 'John had a car which Eve bought. John had a car which Eve saw?', None],
  [837, 'John had a car which Eve bought. John had a car which Mike bought?', None],
  [838, 'John had a car which Mike bought. John had a car Mike bought?', True],
  [839, 'John had a car which Eve bought. John had a car Eve saw?', None],
  [840, 'John had a car which Eve bought. John had a car Mike bought?', None],
  [841, 'John had a car Mike bought. John had a car Mike bought?', True],
  [842, 'John had a car Eve bought. John had a car Mike bought?', None],
  [843, 'John had a car Eve bought. John had a car Eve saw?', None],
  [844, 'John had a car Eve bought. John had a car which Eve bought?', True],
  [845, 'John had a car Eve bought. John had a car which Eve saw?', None],
  [846, 'John had a car Eve bought. John had a car which Mike bought?', None],
  [847, 'John had a car Eve bought. Eve bought a car?', True],

  [848, 'John had a car Eve liked. Eve had a car?', None],

  [849, 'John had a red car Eve bought. John had a car which Eve bought?', True],
  [850, 'John had a red car which Mike bought. John had a car Mike bought?', True],
  [851, 'John had a red car Eve bought. John had a black car which Eve bought?', None],
  [852, 'John had a red car which Eve bought. John had a black car Eve bought?', None],

  [853, 'John had a car Eve bought. John had a car which Eve did not buy?', None],
  [854, 'John had a car which Mike did not buy. John had a car Mike did not buy?', True],
  [855, 'John did not have a red car which Eve bought. John did not have a red car which Eve bought?', True],

  # -- drove + which-clause --

  [856, 'John drove a car which Eve bought. John drove a car which Eve bought?', True],
  [857, 'John drove a car which Eve bought. John drove a car which Eve saw?', None],
  [858, 'John drove a car which Eve bought. John drove a car which Mike bought?', None],
  [859, 'John drove a car which Eve bought. John drove a car Eve bought?', True],
  [860, 'John drove a car which Eve bought. John drove a car Eve saw?', None],
  [861, 'John drove a car which Eve bought. John drove a car Mike bought?', None],
  [862, 'John drove a car Mike bought. John drove a car Mike bought?', True],
  [863, 'John drove a car Eve bought. John drove a car Mike bought?', None],
  [864, 'John drove a car Eve bought. John drove a car Eve saw?', None],
  [865, 'John drove a car Mike bought. John drove a car which Mike bought?', True],
  [866, 'John drove a car Eve bought. John drove a car which Eve saw?', None],
  [867, 'John drove a car Eve bought. John drove a car which Mike bought?', None],
  [868, 'John drove a car Eve bought. Eve drove a car?', None],
  [869, 'John drove a car Eve bought. John drove a car?', True],

  [870, 'John drove a red car Mike bought. John drove a car which Mike bought?', True],
  [871, 'John drove a red car which Eve bought. John drove a car Eve bought?', True],
  [872, 'John drove a red car Eve bought. John drove a black car which Eve bought?', None],
  [873, 'John drove a red car which Eve bought. John drove a black car Eve bought?', None],

  [874, 'John drove a car Eve bought. John drove a car which Eve did not buy?', None],
  [875, 'John drove a car which Mike did not buy. John drove a car Mike did not buy?', True],

  # -- whom-clauses --

  [876, 'John is a man whom Eve liked. John is a man whom Eve liked?', True],
  [877, 'John is a man whom Eve liked. John is a man whom Eve saw?', None],
  [878, 'John is a man whom Eve liked. John is a man whom Mike liked?', None],
  [879, 'John is a man whom Eve liked. John is a man Eve liked?', True],
  [880, 'John is a man whom Eve liked. John is a man Eve saw?', None],
  [881, 'John is a man whom Eve liked. John is a man Mike liked?', None],

  # -- reduced whom-clauses --

  [882, 'John is a man Eve liked. John is a man Eve liked?', True],
  [883, 'John is a man Eve liked. John is a man Mike liked?', None],
  [884, 'John is a man Eve liked. John is a man Eve saw?', None],
  [885, 'John is a man Eve liked. John is a man whom Eve liked?', True],
  [886, 'John is a man Eve liked. John is a man whom Eve saw?', None],
  [887, 'John is a man Eve liked. John is a man whom Mike liked?', None],

  [888, 'John is a strong man Eve liked. John is a strong man whom Eve liked?', True],
  [889, 'John is a strong man whom Eve liked. John is a strong man Eve liked?', True],
  [890, 'John is a strong man Eve liked. John saw a strong man whom Eve liked?', None],
  [891, 'John is a strong man whom Eve liked. John saw a strong man Eve liked?', None],

  [892, 'John is a man Eve liked. John is a man whom Eve did not like?', False],
  [893, 'John is a man whom Eve did not like. John is a man Eve did not like?', True],

  [894, 'John is not a man whom Eve liked. John is not a man whom Eve liked?', True],
  [895, 'John is a man Eve liked. John is a man?', True],
  [896, 'John is a man Eve liked. Eve liked John?', True],
  [897, 'John is a man Mary liked. Mary liked a man?', True],
  [898, 'John is a man Mary liked. Mary liked the man?', True],

  # -- that-clauses --

  [899, 'The book that Mary bought is on the table. Who bought the book?', 'Mary.'],
  [900, 'The book that Mary bought is on the table. Did John buy the book?', None],
  [901, 'The car which John drove was red. What color was the car?', 'Red.'],
  [902, 'The car which John drove was red. Was the car blue?', False],
  [903, 'The student who passed the test studied a lot. Did the student study?', True],
  [904, 'The student who passed the test studied a lot. Did the student fail the test?', False],

  [905, 'The man who laughed and who waved left. The man laughed?', True],
  [906, 'The man who laughed and who waved left. The man waved?', True],
  [907, 'The man who laughed and who waved left. Did the man cry?', None],

  # -- who-clause queries --

  [908, 'The man who saw John is tall. Who saw John?', 'The man.'],
  [909, 'The man who saw John is tall. Did John see the man?', None],
  [910, 'The man whom John saw is tall. Who did John see?', ['The man.', 'The tall man.']],
  [911, 'The man whom John saw is tall. Is the man short?', False],

  # -- have with relative clauses --

  [912, 'A man had a car which a nice woman bought. The car was red. Who bought the red car?', 'The nice woman'],
  [913, 'A man had a car which a nice woman bought. The car was red. Who bought a car?', 'The nice woman'],
  [914, 'A man had a car which a nice woman bought. The car was red. Who was nice?', 'The woman'],
  [915, 'A man had a car which a nice woman bought. The car was red. Who was nice and bought a car?', ['The woman', 'The nice woman.']],
  [916, 'A man had a car which a nice woman bought. The car was red. Who bought the black car?', None],

  [917, 'A big bear was strong. The bear was nice. Who was nice and strong?', ['The big bear.', 'The bear.']],

  [918, 'A big bear was strong. The small bear was nice. Who was nice and strong?', None],
  [919, 'A big bear was strong. The small bear was nice. Who was nice?', 'The small bear.'],
  [920, 'A big bear was strong. The small bear was nice. Who was strong?', 'The big bear.'],

  [921, 'A bear was strong. The bear was nice. Who was nice and strong?', 'The bear.'],
  [922, 'The big bear is strong. Who is strong?', 'The big bear'],
  [923, 'A man liked a car. The man did not like the car?', False],

  [924, 'A man liked a car which a woman bought. The car was red. A man liked a car?', True],
  [925, 'A man liked a car which a woman bought. The car was red. The man liked the car?', True],
  [926, 'A man liked a car which a woman bought. The car was red. The man liked a red car?', True],
  [927, 'A man liked a car which a woman bought. The car was red. The man liked the bike?', None],
  [928, 'A man liked a car which a woman bought. The car was red. The man liked a black car?', None],
  [929, 'A man liked a car which a woman bought. The car was red. The man liked the red car?', True],

  # -- indefinite subject with which-clause --

  [930, 'A man had a car which a woman bought. A man had a car which a woman bought?', True],
  [931, 'A man had a car a woman bought. A man had a car which a woman bought?', True],
  [932, 'A man had a car which a woman bought. A man had a car which a woman liked?', None],
  [933, 'A man had a car which a woman bought. A man had a car which a man bought?', None],
  [934, 'A man had a car a woman bought. A woman bought a car?', True],
  [935, 'A man had a car a woman bought. The woman bought a car?', True],
  [936, 'A man had a car a woman bought. The woman did not buy a car?', False],
  [937, 'A man had a car a woman bought. A man had a bike?', None],
  [938, 'A man had a car a woman bought. A woman bought a red car?', None],
  [939, 'A man had a car a woman bought. A man bought a car?', None],
  [940, 'A man had a car a woman bought. The man did not have a car?', False],

  # -- indefinite drove + which --

  [941, 'A man drove a car which a woman bought. A man drove a car which a woman bought?', True],
  [942, 'A man drove a car a woman bought. A man drove a car which a woman bought?', True],
  [943, 'A man drove a car which a woman bought. A man drove a car a woman bought?', True],
  [944, 'A man drove a car which a woman bought. A man drove a car which a woman liked?', None],
  [945, 'A man drove a car which a woman bought. A man drove a car?', True],
  [946, 'A man drove a car which a woman bought. A man drove the car?', True],
  [947, 'A man drove a car which a woman bought. A woman drove the car?', None],
  [948, 'A man drove a car which a woman bought. A woman bought a car?', True],
  [949, 'A man drove a car which a woman bought. A woman bought the car?', True],

  [950, 'A man had a car which a woman bought. A man had a car?', True],
  [951, 'A man had a car which a woman bought. A man had the car?', True],
  [952, 'A man had a car which a woman bought. A woman bought a car?', True],
  [953, 'A man had a car which a woman bought. A woman bought the car?', True],

  # -- which-clause with follow-up facts --

  [954, 'A man had a car which a woman bought. The car was red. A man had a car?', True],
  [955, 'A man had a car which a woman bought. The car was red. The man had the car?', True],
  [956, 'A man had a car which a woman bought. The car was red. The man had a red car?', True],
  [957, 'A man had a car which a woman bought. The car was red. The man had the bike?', None],
  [958, 'A man had a car which a woman bought. The car was red. The man had a black car?', None],
  [959, 'A man had a car which a woman bought. The car was red. The man had the red car?', True],
  [960, 'A man had a car which a woman bought. The car was red. The man had the car which a woman bought?', True],
  [961, 'A man had a car which a woman bought. The car was red. The man had the red car which a woman bought?', True],
  [962, 'A man had a car which a woman bought. The car was red. The man had a car which a boy bought?', None],
  [963, 'A man had a car which a woman bought. The car was red. A man had a red car which a woman bought?', True],
  [964, 'A man had a car which a woman bought. The car was red. The man did not have the red car which a woman bought?', False],

  [965, 'A man had a car which he bought. The car was red. The man bought the red car?', True],
  [966, 'A man had a car which he bought. The car was red. A man bought a red car?', True],

  # -- nested who/which clauses --

  [967, 'Bears who eat fish which are big are strong. John is a bear. John eats fish. John is strong?', None],
  [968, 'Bears who eat fish which are big are strong. John is a bear. John eats big apples. John is strong?', None],

  # -- nested who+which clauses --

  [969, """A man who ate breakfast liked a car which a woman bought. The car was red.
     A man who ate breakfast liked a red car which a woman bought?""", True],
  [970, """A man who ate breakfast liked a car.
     The man ate breakfast?""", True],
  [971, """A man who ate breakfast liked a car which a woman bought. The car was red.
     The man who ate breakfast liked the red car which the woman bought?""", True],
  [972, """A man who ate breakfast liked a car which a woman bought. The car was red.
     The man who ate breakfast liked the red car which a woman bought?""", True],

  [973, 'A man liked a car which a woman bought. The car was red. Who liked a red car?', 'The man'],

  [974, 'A man liked a car which a nice woman bought. The car was red. Who bought the red car?', 'The nice woman'],
  [975, 'A man liked a car which a nice woman bought. The car was red. Who bought a car?', 'The nice woman'],
  [976, 'A man liked a car which a nice woman bought. The car was red. Who was nice?', 'The woman'],
  [977, 'A man liked a car which a nice woman bought. The car was red. Who was nice and bought a car?', 'The woman'],
  [978, 'A man liked a car which a nice woman bought. The car was red. Who bought the black car?', None],

  # -- complex: who + which + follow-up --

  [979, """A man who ate breakfast had a car which a woman bought. The car was red.
     A man who ate breakfast had a red car which a woman bought?""", True],
  [980, """A man who ate breakfast had a car.
     The man ate breakfast?""", True],
  [981, """A man who ate breakfast had a car which a woman bought. The car was red.
     The man who ate breakfast had the red car which the woman bought?""", True],
  [982, """A man who ate breakfast had a car which a woman bought. The car was red.
     The man who ate breakfast had the red car which a woman bought?""", True],

# == AMBIGUOUS MODIFIER SCOPE ==

  # -- manner adverb --

  [983, 'John ate the apple quickly. How did John eat the apple?', 'Quickly.'],
  [984, 'John ate the apple quickly. Did John eat a banana?', None],
  [985, 'Mary visited London in September. When did Mary visit London?', 'In September.'],
  [986, 'Mary visited London in September. Did Mary visit Paris?', None],

  # -- adjectival modifier --

  [987, 'The blue bird sang a beautiful song. What color was the bird?', 'Blue.'],
  [988, 'The blue bird sang a beautiful song. Was the bird red?', False],
  [989, 'The tall man walked into the small room. Who walked into the room?', ['The tall man.', 'The man.']],
  [990, 'John works at the hospital every day. Where does John work?', 'At the hospital.'],
  [991, 'John works at the hospital every day. Does John work at the school?', None],

  # -- instrument PP --

  [992, 'John ate berries with the help of a spoon. John ate berries with the help of a spoon?', True],
  [993, 'John ate berries with the help of a spoon. John ate berries with the help of a spade?', None],

  # -- with-PP ambiguity --

  [994, 'John saw the man with a telescope. John saw the man?', True],

  # -- in-PP ambiguity --

  [996, 'John saw the bird in the garden. John saw the bird?', True],
  [997, 'John saw the bird in the garden. The bird was in the garden?', True],
  [998, 'John saw the bird in the garden. Did John see a fish in the garden?', None],

  # -- on-PP ambiguity --

  [999, 'John ate the pizza on the table. Where was the pizza?', 'On the table.'],
  [1000, 'John ate the pizza on the table. Was the pizza on the floor?', False],
  [1001, 'John ate the pizza on the table. Did John eat a sandwich?', None],

  [1002, 'The cat in the hat sat on the mat. Where was the cat?', ['In the hat.', 'On the mat.']],
  [1003, 'Mary put the book on the shelf in the library. Where is the shelf?', 'In the library.'],
  [1004, 'Mary put the book on the shelf in the library. Did Mary put a magazine on the shelf?', None],

  # -- under-PP --

  [1005, 'Mary found the key under the table. Mary found the key?', True],
  [1006, 'Mary found the key under the table. The key was under the table?', True],
  [1007, 'Mary found the key under the table. Was the key on the table?', False],

  [1008, 'Tom put the book on the chair. The book was on the chair?', True],
  [1009, 'Eve kept the milk in the fridge. The milk was in the fridge?', True],

  # -- from-PP --

  [1010, 'John met the girl from Paris. John met the girl?', True],
  [1011, 'John met the girl from Paris. The girl was from Paris?', True],
  [1012, 'Mary called the boy in the kitchen. Mary called the boy?', True],
  [1013, 'Mary called the boy in the kitchen. The boy was in the kitchen?', True],

  # -- classic PP-attachment ambiguity --

  [1015, 'John shot an elephant in his pyjamas. John shot in his pyjamas?', True],

  [1016, 'John ate berries in a forest with a spoon. John ate berries in a forest with a spoon?', True],
  [1017, 'John ate berries in a forest with a spoon. John ate berries in a field?', None],
  [1018, 'John ate berries in a forest with a spoon. John ate berries in a nice forest with a spoon?', None],
  [1019, 'John ate berries in a forest with a spoon. John ate berries in a nice forest?', None],
  [1020, 'John ate berries in a forest with a spoon. John ate berries with a spoon in a nice forest?', None],

# == PASSIVE VOICE ==

  # -- basic passive --

  [1021, 'John is defeated. Mike is defeated?', None],
  [1022, 'John is defeated. John is defeated?', True],
  [1023, 'John is defeated. Who is defeated?', 'John'],
  [1024, 'John is defeated. John is not defeated?', False],
  [1025, 'John and Mike were defeated. Who defeated John?', None],
  [1026, 'John and Mike were defeated. Who defeated John and Mike?', None],

  [1027, 'An apple was eaten. John ate a pear. What was eaten?', ['The apple and the pear.', 'An apple and a pear.', 'An apple.', 'A pear.']],
  [1028, 'John was nice and defeated. John was nice and defeated?', True],
  [1029, 'John was nice and defeated. John was nice?', True],
  [1030, 'John was defeated. John was defeated?', True],

  # -- active/passive equivalence --

  [1031, 'Clinton defeated Dole. Clinton defeated Dole?', True],
  [1032, 'Clinton defeated Dole. Clinton defeated Mike?', None],
  [1033, 'Dole was defeated by Clinton. Dole was defeated by Clinton?', True],
  [1034, 'Dole was defeated by Clinton. Dole was defeated by Mike?', None],
  [1035, 'Clinton defeated Dole. Dole was defeated by Clinton?', True],
  [1036, 'Clinton defeated Dole. Dole was defeated by Mike?', None],
  [1037, 'Dole was defeated by Clinton. Clinton defeated Dole?', True],
  [1038, 'Dole was defeated by Clinton. Mike defeated Dole?', None],

  # -- passive with by-phrase --

  [1039, 'The window was broken by John. John broke the window?', True],
  [1040, 'The window was broken by John. Did Mary break the window?', None],
  [1041, 'The song was sung by Mary. Mary sang the song?', True],
  [1042, 'The letter was written by Eve. Eve wrote the letter?', True],
  [1043, 'The letter was written by Eve. Did Tom write the letter?', None],
  [1044, 'The house was built by Tom. Tom built the house?', True],
  [1045, 'The house was built by Tom. Tom destroyed the house?', None],
  [1046, 'The bicycle was repaired by Anna. Anna repaired the bicycle?', True],
  [1047, 'The bicycle was repaired by Anna. Anna broke the bicycle?', None],
  [1048, 'The cake was eaten by the child. The child ate the cake?', True],
  [1049, 'The ball was kicked by Mike. Mike kicked the ball?', True],
  [1050, 'The ball was kicked by Mike. Did Mike catch the ball?', None],
  [1051, 'The tree was cut by the farmer. The farmer cut the tree?', True],
  [1052, 'The book was read by Sara. Sara read the book?', True],
  [1053, 'The book was read by Sara. Did Sara write the book?', None],
  [1054, 'The car was washed by Paul. Paul washed the car?', True],
  [1055, 'The room was cleaned by the maid. The maid cleaned the room?', True],
  [1056, 'The picture was painted by Leo. Leo painted the picture?', True],

  # -- agentless passive --

  [1057, 'The window was broken. John broke the window?', None],
  [1058, 'The letter was written. Mary wrote the letter?', None],
  [1059, 'The cake was eaten. Who ate the cake?', None],
  [1060, 'The room was cleaned. Who cleaned the room?', None],
  [1061, 'The glass was broken by the boy. Who broke the glass?', 'The boy.'],

  # -- passive ditransitive --

  [1062, 'Mary was given a promotion. Who received a promotion?', 'Mary.'],
  [1063, 'A promotion was given to Mary. What did Mary get?', 'A promotion.'],
  [1064, 'The city was destroyed. Is the city destroyed?', True],
  [1065, 'The city was destroyed. Is the city intact?', False],
  [1066, 'The mouse was chased by the cat. Who was the cat chasing?', 'The mouse.'],
  [1067, 'The bill was paid by John. Did John pay the bill?', True],
  [1068, 'The bill was paid by John. Did Mary pay the bill?', None],

# == SUBORDINATE CLAUSES ==

  # -- reported speech --

  [1069, 'John said that Mary left. Mary left?', True],
  [1070, 'John said that Mary left. Did Mary stay?', None],
  [1071, 'Eve reported that Tom arrived. Tom arrived?', True],
  [1072, 'Eve reported that Tom arrived. Did Tom depart?', None],
  [1073, 'Anna announced that the show started. The show started?', True],
  [1075, 'The guide explained that the road was closed. Was the road open?', False],

  # -- infinitival purpose clause --

  [1076, 'John went to the shop to buy bread. John went to the shop?', True],
  [1077, 'John went to the shop to buy bread. John bought bread?', None],
  [1078, 'John went to the shop to buy bread. Did John go to the bank?', None],

  [1079, 'Mary opened the window to let in air. Mary opened the window?', True],
  [1080, 'Mary opened the window to let in air. Mary did not open the window?', False],
  [1081, 'Mary opened the window to let in air. Air came in?', None],

  # -- concessive: although --

  [1082, 'Although John was tired, he finished the work. John was tired?', True],
  [1083, 'Although John was tired, he finished the work. John finished the work?', True],
  [1084, 'Although John was tired, he finished the work. John did not finish the work?', False],
  [1085, 'Although John was tired, he finished the work. Was the work difficult?', None],

  # -- concessive: though --

  [1086, 'Though Mary was ill, she traveled. Mary was ill?', True],
  [1087, 'Though Mary was ill, she traveled. Mary traveled?', True],
  [1088, 'Though Mary was ill, she traveled. Mary did not travel?', False],
  [1089, 'Though Mary was ill, she traveled. Did Mary recover?', None],

  # -- sentence adverbials --

  [1090, 'Fortunately, John found the key. John found the key?', True],
  [1091, 'Fortunately, John found the key. John did not find the key?', False],
  [1092, 'Fortunately, John found the key. Did John find the lock?', None],

  [1093, 'Sadly, Mary lost the letter. Mary lost the letter?', True],
  [1094, 'Unexpectedly, the door opened. The door opened?', True],
  [1095, 'Unexpectedly, the door opened. The door did not open?', False],
  [1096, 'Apparently, Tom left early. Tom left early?', True],

  [1097, 'Mary said that she was tired. Who was tired?', 'Mary.'],
  [1098, 'Mary said that she was tired. Was Mary happy?', None],
  [1099, 'A surgeon, Dr. Smith, entered the room. Who entered the room?', ['Dr. Smith.', 'A surgeon.']],
  [1100, 'The horse kept in the stable was calm. The horse was in the stable?', True],

# == ELLIPSIS & GAPPING ==

  # -- gapping --

  [1101, 'John likes tea and Mary coffee. What does Mary like?', 'Coffee.'],
  [1102, 'John likes tea and Mary coffee. Does Mary like tea?', None],

  # -- locative gapping --

  [1103, 'John went to Paris and Mary to London. Where did Mary go?', ['London.', 'To London.']],
  [1104, 'Paul ate a sandwich and Bill a salad. What did Bill eat?', 'A salad.'],
  [1105, 'Paul ate a sandwich and Bill a salad. Did Paul eat a salad?', None],

  # -- VP ellipsis with did-too --

  [1106, 'John saw the doctor and Mary did too. Did Mary see the doctor?', True],
  [1107, 'John saw the doctor and Mary did too. Did Mary see the dentist?', None],
  [1108, 'John bought a book, and Bill said Peter did too. Did Bill say Peter bought a book?', True],

  # -- conditional did-too --

  [1109, 'If John wrote a report, then Bill did too. John wrote a report. Did Bill write a report?', True],
  [1110, 'If John wrote a report, then Bill did too. John wrote a report. Did Bill write a novel?', None],

# == ACTION MODES & HABITS ==

  # -- action with location --

  [1111, 'Bears eat berries in a forest. Bears eat berries in a forest?', True],
  [1112, 'Bears eat berries in a forest. Bears eat berries in a big forest?', None],
  [1113, 'Bears do not eat berries in a forest. Bears eat berries in a forest?', False],

  # -- action with manner adverb --

  [1114, 'Bears quickly eat berries in a forest. Bears eat berries?', True],
  [1115, 'Bears quickly eat berries in a forest. Bears quickly eat berries?', True],
  [1116, 'Bears quickly eat berries in a forest. Bears slowly eat berries?', None],

  [1117, 'Bears eat red berries in a forest. Bears eat berries in forest?', True],
  [1118, 'Bears do not eat red berries in a forest. Bears eat red berries in forest?', False],

  [1119, 'Bears eat berries in a deep forest. Bears eat berries?', True],
  [1120, 'Bears eat berries in a deep forest. Bears eat berries in a deep forest?', True],
  [1121, 'Bears eat berries in a deep forest. Bears eat berries in a forest?', True],
  [1122, 'Bears eat berries in a deep forest. Bears eat berries in a shallow forest?', None],

  # -- action with modified arguments --

  [1123, 'Bears eat red berries in a deep forest. John is a bear. John eats red berries in a deep forest?', True],
  [1124, 'Bears eat red berries in a deep forest. John is a bear. John eats no berries?', False],
  [1125, 'Bears eat berries in a deep forest. John is a bear. John eats berries in a shallow forest?', None],
  [1126, 'Bears quickly eat berries in a deep forest. John is a bear. John quickly eats berries in a deep forest?', True],

  [1127, """If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John quickly eats berries in a deep forest. John is hungry?""", True],
  [1128, """If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John eats berries in a deep forest. John is hungry?""", None],
  [1129, """If a bear quickly eats berries in a deep forest, it is hungry. John is a fox.
     John quickly eats berries in a deep forest. John is hungry?""", None],

  [1130, """If a bear eats berries in a forest, it is hungry. John is a brown bear.
      John quickly eats berries in a deep forest. Who is hungry?""", 'John.'],
  [1131, """If a bear eats berries in a forest, it is hungry. John is a brown bear.
      John draws berries in a deep forest. Who is hungry?""", None],
  [1132, """If a bear eats, it is hungry. John is a brown bear.
      John quickly eats berries in a deep forest. Who is hungry?""", 'John.'],

  # -- habitual location --

  [1133, 'Penguins live in the water. Penguins live in the water?', True],
  [1134, 'Penguins live in the water. Penguins live in water?', True],
  [1135, 'Penguins live in the water. Penguins live in stone?', None],
  [1136, 'Penguins live in the water. Penguins live in the stone?', None],
  [1137, 'Penguins live in water. Penguins live in water?', True],
  [1138, 'Penguins live in water. Penguins live in stone?', None],
  [1139, 'Penguins live in water. Penguins live in the stone?', None],

  [1140, 'Penguins happily live in cold water. Penguins live in water?', True],
  [1141, 'Penguins happily live in cold water. Penguins live in cold water?', True],

  [1143, 'Bears eat berries in a forest. Bears eat berries in forest?', True],
  [1144, 'Bears eat berries in a forest. Bears do not eat berries in forest?', False],
  [1145, 'Bears eat berries in a forest. Bears eat berries in a field?', None],
  [1146, 'Bears eat berries in a forest. Bears eat berries?', True],

# == TRANSFER OF POSSESSION (GIVE/TAKE) ==

  # -- basic give/receive --

  [1147, 'John gave Mary a book. Who received a book?', 'Mary.'],
  [1148, 'John gave Mary a book. Did John receive a book?', None],
  [1149, 'John gave a book to Mary. What did Mary receive?', ['A book.', 'The book.']],
  [1150, 'John gave a book to Mary. Did Eve receive a book?', None],

  # -- hand: transfer variant --

  [1151, 'Anna handed Mark a key. Mark got a key?', True],
  [1152, 'Anna handed a key to Mark. Anna handed Mark a key?', True],
  [1153, 'Anna handed a key to Mark. Did Anna hand Mark a lock?', None],

  # -- show/see inference --

  [1154, 'The teacher showed the students the map. Who saw the map?', ['The students.', 'The teacher and the students.']],
  [1155, 'The teacher showed the students the map. Did the teacher show a book?', None],
  [1156, 'The teacher showed the map to the students. What did the teacher show?', 'The map.'],

  # -- tell: communication transfer --

  [1157, 'John told Mary a story. Mary heard a story?', True],
  [1158, 'John told Mary a story. Did Mary tell John a story?', None],
  [1159, 'John told a story to Mary. Who heard a story?', 'Mary.'],

  [1160, 'The guide offered the tourists tea. Did the guide offer coffee?', None],

  # -- for-benefactive --

  [1161, 'The chef cooked a meal for the guests. Who was the meal for?', 'The guests.'],
  [1162, 'The chef cooked a meal for the guests. Did the chef eat the meal?', None],

  # -- reflexive transfer --

  [1163, 'Susan bought herself a new car. Who owns a new car?', 'Susan.'],
  [1164, 'Susan bought herself a new car. Did Tom buy a car?', None],
  [1165, 'Susan bought a new car for herself. What did Susan buy?', ['A new car.', 'A car.']],

  [1166, 'John gave Mary a book. Mary got a book?', True],
  [1167, 'John gave Mary a book. Did Mary give John a book?', None],
  [1168, 'John gave a book to Mary. Mary got a book?', True],

  [1169, 'Eve sent Tom a letter. Did Tom send Eve a letter?', None],
  [1170, 'Eve sent a letter to Tom. Who got a letter?', 'Tom.'],
  [1171, 'The teacher showed the students a map. The students saw a map?', True],
  [1172, 'The teacher showed the students a map. Did the students see a globe?', None],
  [1173, 'The teacher showed a map to the students. Who saw a map?', ['The students.', 'The teacher and the students.']],

  # -- give with modified object --

  [1174, 'John gave Mary a red book. Mary got a red book?', True],
  [1175, 'John gave Mary a red book. Mary got a blue book?', None],
  [1176, 'Eve sent Tom a long letter. Tom got a short letter?', None],
  [1177, 'Anna handed Mark a silver key. Mark got a silver key?', True],
  [1178, 'The teacher showed the students a large map. The students saw a large map?', True],
  [1179, 'The teacher showed the students a large map. Did the students see a small map?', None],

  [1180, 'Bears eat red berries in a forest. Bears eat red berries in forest?', True],
  [1181, 'Bears eat red berries in a forest. Bears eat yellow berries in forest?', None],

# == TENSE, ASPECT & CHANGE OF STATE ==

  # -- did-emphasis --

  [1182, 'A man did have a car. A man had a car?', True],
  [1183, 'A man had a car. A man did have a car?', True],
  [1184, 'The man has a car. The man does have a car?', True],
  [1185, 'A man had a car. A man has a car?', True],
  [1186, 'A man had a car. The man has a car?', True],

  # -- perfective aspect --

  [1187, 'John has finished his homework. Is the homework finished?', True],
  [1188, 'John has finished his homework. Is the homework unfinished?', False],
  [1189, 'John has finished his homework. Has John finished his project?', None],

  # -- progressive aspect --

  [1191, 'Mary was reading a book when the phone rang. Did the doorbell ring?', None],

  # -- future tense --


  # -- present for scheduled events --

  [1192, 'The train leaves at noon. When does the train leave?', 'At noon.'],

  # -- temporal subordinate: before --

  [1193, 'Before John left, he locked the door. John locked the door?', True],
  [1194, 'Before John left, he locked the door. John left?', True],
  [1195, 'Before John left, he locked the door. Did John lock the window?', None],

  # -- temporal subordinate: after --

  [1196, 'After Mary arrived, she called Tom. Mary arrived?', True],
  [1197, 'After Mary arrived, she called Tom. Mary called Tom?', True],
  [1198, 'After Mary arrived, she called Tom. Did Mary call Eve?', None],

  # -- temporal subordinate: when --

  [1199, 'When Eve entered the house, she smiled. Eve entered the house?', True],
  [1200, 'When Eve entered the house, she smiled. Eve did not enter the house?', False],
  [1201, 'When Eve entered the house, she smiled. Eve smiled?', True],

  # -- temporal subordinate: while --

  [1202, 'While John was cooking, Mary read a book. John cooked?', True],
  [1203, 'While John was cooking, Mary read a book. Did John read a book?', None],
  [1204, 'While John was cooking, Mary read a book. Mary read a book?', True],

  [1205, 'As Tom walked home, it rained. Tom walked home?', True],
  [1206, 'As Tom walked home, it rained. It rained?', True],
  [1207, 'As Tom walked home, it rained. Did it snow?', None],

  # -- temporal subordinate: once --

  [1208, 'Once Anna found the key, she opened the box. Anna found the key?', True],
  [1209, 'Once Anna found the key, she opened the box. Anna opened the box?', True],
  [1210, 'Once Anna found the key, she opened the box. Did Anna close the box?', None],

  # -- temporal subordinate: since --

  [1211, 'Since Mike lost his ticket, he stayed outside. Mike lost his ticket?', True],
  [1212, 'Since Mike lost his ticket, he stayed outside. Mike stayed outside?', True],
  [1213, 'Since Mike lost his ticket, he stayed outside. Did Mike find his ticket?', None],

  [1214, 'Until Sara arrived, John waited. Sara arrived?', True],
  [1215, 'Until Sara arrived, John waited. John waited?', True],

  [1216, 'After John bought a car, he washed it. John bought a car?', True],
  [1217, 'After John bought a car, he washed it. John washed the car?', True],
  [1218, 'After John bought a car, he washed it. Did John sell the car?', None],

  [1219, 'Before Mary wrote a letter, she found a pen. Mary found a pen?', True],
  [1220, 'Before Mary wrote a letter, she found a pen. Did Mary find a pencil?', None],

  # -- change-of-state verbs --

  [1221, 'John stopped smoking. Did John smoke in the past?', True],
  [1222, 'John stopped smoking. Does John smoke now?', False],
  [1223, 'Mary started the car. Was the car running before?', False],
  [1224, 'The rain continued. Was it raining earlier?', True],

# == SPATIAL LOGIC & WHERE QUERIES ==

  # -- basic location assertions --

  [1225, 'We are in the barn. We are in the barn?', True],
  [1226, 'We are in the barn. We are in the shop?', None],
  [1227, 'We are in the barn. We are on the barn?', None],

  [1228, 'Agatha is in trouble. Agatha is in trouble?', True],
  [1229, 'Agatha is in trouble. Agatha is in the barn?', None],
  [1230, 'Agatha is in trouble. Agatha is through trouble?', None],

  # -- existential location --

  [1231, 'There is a ghost in the room. There is a ghost in the room?', True],
  [1232, 'There is a ghost in the room. A ghost is in the room?', True],
  [1233, 'There is a ghost in the room. There is a lamp in the room?', None],
  [1234, 'There is a ghost in the room. There is a ghost in the barn?', None],

  [1235, 'These links present the many viewpoints that existed. These links present the lemmas that existed?', None],

  # -- basic where-questions --

  [1236, 'John is in a box. Mark is in a house. Where is John?', ['In the box.', 'In a box.']],
  [1237, 'John is in a box. Mark is in a house. Where is Mark?', 'In the house.'],
  [1238, 'John is on a box. Mark is on a house. Where is John?', ['On the box.', 'On a box.']],
  [1239, 'John is on a box. Mark is on a house. Where is Mark?', ['On the house.', 'On a house.']],
  [1240, 'John is at a box. Mark is at a house. Where is John?', ['At the box.', 'At a box.']],
  [1241, 'John is at a box. Mark is at a house. Where is Mark?', ['At the house.', 'At a house.']],

  [1242, 'John is near a box. Mark is near a house. Where is John?', ['Near the box.', 'Near a box.']],
  [1243, 'John is near a box. Mark is near a house. Where is Mark?', ['Near the house.', 'Near a house.']],
  [1244, 'John is under a box. Mark is under a house. Where is John?', ['Under the box.', 'Under a box.']],
  [1245, 'John is under a box. Mark is under a house. Where is Mark?', ['Under the house.', 'Under a house.']],
  [1246, 'John is above a box. Mark is above a house. Where is John?', ['Above the box.', 'Above a box.']],
  [1247, 'John is above a box. Mark is above a house. Where is Mark?', ['Above the house.', 'Above a house.']],
  [1248, 'A car is in a box and in a house. Where is the car?', ['In the house and in the box.', 'In a box and in a house.', 'In a house.', 'In a box.']],
  [1249, 'A car was in a box and in a house. Where was the car?', ['In the house and in the box.', 'In a box and in a house.', 'In a box.', 'In a house.']],
  [1250, 'John is in the box and in the red house. Where is John?', 'In the box and in the red house.'],

  # -- conjunction in location --

  [1251, 'John is in a box and house. Mark is near the house. Where is John?', ['In the house and in the box.', 'In a box and house.', 'In a box.']],
  [1252, 'John is in a box and house. Mark is near the house. Where is Mark?', 'Near the house.'],

  # -- containment and transitivity --

  [1253, """Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. Tallinn is in what?""", ['Earth, Europe and Estonia.', 'Estonia.', 'Europe.', 'Earth.']],
  [1254, """Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. What is not in Estonia?""", 'Riga.'],
  [1255, """Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. Riga is in Estonia?""", False],

  [1256, '"Riga is outside America. Riga is not in what?', 'America.'],
  [1257, '"Riga is not in America. What is not in America?', 'Riga.'],

  # -- spatial rules --

  [1258, """If a city is in Estonia, it is an Estonian city. Tallinn is in Estonia. Tallinn is a city.
     What is an Estonian city?""", 'Tallinn.'],
  [1259, """Cities in Estonia are estonian. Tallinn is in Estonia. Tallinn is a city.
    What is an Estonian city?""", 'Tallinn.'],

  # -- spatial conditionals --

  [1260, 'If John is in a box, he is in the house. John is in the box. Mark is not in the box. Where is John?', ['In the box and in the house.', 'In the house.', 'In the box.']],
  [1261, 'If a car is in a box, the car is in the house. A red car is in the box. Where is a car?', ['In the box and in the house.', 'In the house.', 'In the box.']],
  [1262, 'John is not in the box. John is in the red house. Where is John?', 'In the red house.'],
  [1263, 'The black car is not in the box. The car is in the red house. Where is the car?', 'In the red house.'],
  [1264, 'John is in a box. John is near a spoon. John is on the floor. Where is John?', ['Near the spoon, in the box and on the floor.', 'In a box.', 'On the floor.', 'Near a spoon.', 'In a box on the floor.']],
  [1265, 'John is in a box. John is near a spoon. John is on the floor. John is not in the box. Where is John?', ['On the floor and near the spoon.', 'On the floor.']],
  [1266, 'John is in a box. John is near a spoon. John is on the floor. John is not in the box. Where is John?', ['On the floor and near the spoon.', 'On the floor.', 'Near a spoon.']],

  # -- chained location --

  [1267, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the black car?""", ['In the street and in Tallinn.', 'In the street.', 'In Tallinn.']],
  [1268, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the red car?""", 'In the house.'],
  [1269, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is a car?""", ['In the house, in the street and in Tallinn.', 'In the house.', 'In the street.', 'In the house and in the street.', 'In Tallinn.']],
  [1270, """John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the man?""", ['In the red car and in the house.', 'In the house.', 'In the red car.']],

  # -- nested location --

  [1271, 'John is in the box which is in the red house. Where is John?', ['In the box and in the red house.', 'In the red house.', 'In the box.']],
  [1272, 'John is in the box which is in the red house. Where is the box?', 'In the red house.'],

  [1273, 'John is in the box which is near the red house. Where is John?', ['In the box.', 'Near the red house.', 'In the box near the red house.']],
  [1274, 'John is in the box which is near the red house. Where is the box?', 'Near the red house.'],
  [1275, 'John is in the box near the red house. Where is John?', ['In the box.', 'In the box near the red house.']],

  [1276, 'John is in the box in the red house. Where is John?', ['In the box and in the red house.', 'In the box in the red house.', 'In the box.', 'In the red house.']],
  [1277, 'John is in the box near the red house. Where is the box?', 'Near the red house.'],

  [1278, 'John is in the box at the red house. A box is at a house?', True],
  [1279, 'John is in the box at a red house. The box is at a house?', True],
  [1280, 'John is in the box at a red house. The red box is at a house?', None],
  [1281, 'John is in the box at a red house. The box is at a blue house?', None],
  [1282, 'John is in a box at the red house. A box is at a house?', True],
  [1283, 'John is in a box at the red house. The box is at a house?', True],
  [1284, 'John is in a box at the red house. A box is at the red house?', True],

  # -- location of general terms --

  [1285, 'Birds are in the box. Where are birds?', 'In the box.'],
  [1286, 'The birds are in the box. Where are the birds?', 'In the box.'],
  [1287, 'The birds are in the box. Where are birds?', 'In the box.'],

  [1288, 'Birds near Tallinn are nice. John is near Tallinn. What is near Tallinn?', ['A bird near Tallinn', 'John.', 'John and birds.']],
  [1289, 'Birds near Tallinn are nice. John is near Tallinn. Who is near Tallinn?', 'John'],
  [1290, 'Birds near Tallinn are nice. John is near Tallinn. What is nice?', 'A bird near Tallinn'],
  [1291, 'Birds near Tallinn are nice. John is near Tallinn. John is a bird. Who is nice?', 'John'],

  [1292, 'Birds near Tallinn are nice. John is a bird who is near Tallinn. Who is nice?', 'John'],

  # -- location of actions --

  [1293, 'John ate candy in a house. John ate meat in a room. Where did John eat candy?', 'In a house'],
  [1294, 'John ate candy in a house. John ate meat in a room. Where did John eat meat?', 'In a room'],
  [1295, 'John ate candy in a house. John ate meat at a room. Where did John eat?', ['At a room and in a house', 'In a house and at a room.', 'In a house.', 'At a room.']],

  [1296, 'John jumped high in a room. John jumped low near the garage. Where did John jump?', ['In a room and near the garage', 'In a room.', 'Near the garage.']],
  [1297, 'John jumped high in a room. John jumped low near the garage. Where did John jump high?', 'In a room'],
  [1298, 'John jumped high in a room. John jumped low near the garage. Where did John jump low?', 'Near the garage'],
  [1299, 'John jumped high in a room. John jumped low near the garage. Where did John jump quickly?', None],

  # -- location via relative clause --

  [1300, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate?', True],
  [1301, 'Bears ate berries in a forest which was seen by Mary. Mary saw the forest where the bears ate?', True],

  [1302, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears drank?', None],
  [1303, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate berries?', True],
  [1304, 'Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate honey?', None],

  [1306, 'John lives in a red car bought by Mary. Mary bought the car where John ate?', None],
  [1307, 'John lives in a red car bought by Mary. Mary bought the car where Mike lives?', None],

  # -- temporal-spatial --

  [1308, 'During 1800, John jumped in a house. During 1800, John jumped?', True],
  [1309, 'During 1800, John jumped in a house. During 1801, John jumped?', None],
  [1310, 'During 1800, John jumped in a house. When did John jump?', ['During the year 1800', 'During 1800.']],
  [1311, 'During 1800, John jumped in a house. Where did John jump?', 'In a house'],

  [1312, 'Before 1900, John jumped in a house. When did John jump?', ['Before the year 1900', 'Before 1900.']],
  [1313, 'Before 1900, John jumped in a house. After 1902, John ate in a house. When did John jump?', ['Before the year 1900', 'Before 1900.']],
  [1314, 'Before 1900, John jumped in a house. After 1902, John sat in a house. When did John sat?', ['After the year 1902', 'After 1902.']],
  [1315, 'On Monday, John jumped in a house. Where did John jump?', 'In a house'],
  [1316, 'On Monday, John jumped in a house. When did John jump?', 'On Monday'],
  [1317, 'The cat slept on the velvet sofa. Where did the cat sleep?', ['On the velvet sofa.', 'On the sofa.']],

  [1318, 'The book that Mary bought is on the table. Where is the book?', 'On the table.'],
  [1319, 'The cake that was on the counter has disappeared. Where was the cake?', 'On the counter.'],
  [1320, 'The cat sat on the mat and purred. Where did the cat sit?', 'On the mat.'],

# == ACTION AND WORLD STATE SEQUENCES ==

  # -- bAbI: single supporting fact --

  [1321, 'John travelled to the hallway. Mary journeyed to the bathroom. Where is John?', ['hallway', 'In the hallway.', 'At the hallway.']],

  [1322, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. Where is Mary?', ['bathroom', 'In the bathroom.', 'At the bathroom.']],
  [1323, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Where is Sandra?', ['kitchen', 'In the kitchen.', 'At the kitchen.']],
  [1324, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Sandra travelled to the hallway. John went to the garden. Where is Sandra?', ['hallway', 'In the hallway.', 'At the hallway.']],
  [1325, 'John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Sandra travelled to the hallway. John went to the garden. Sandra went back to the bathroom. Sandra moved to the kitchen. Where is Sandra?', ['kitchen', 'In the kitchen.', 'At the kitchen.']],

  # -- bAbI: multi-step tracking --

  [1326, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Where is Sandra?', ['hallway', 'In the hallway.', 'At the hallway.']],
  [1327, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Where is Sandra?', ['garden', 'In the garden.', 'At the garden.']],
  [1328, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Where is Daniel?', ['hallway', 'In the hallway.', 'At the hallway.']],
  [1329, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. Where is Sandra?', ['office', 'In the office.', 'At the office.']],
  [1330, 'Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. John travelled to the bathroom. John journeyed to the office. Where is Daniel?', ['office', 'In the office.', 'At the office.']],

  [1331, 'The dog was barking and the cat was too. Was the cat barking?', True],
  [1332, 'Eve planned to travel. Eve traveled?', None],



# == QUESTION LOGIC (WHO/WHAT/WHICH) ==

  [1333, 'John is nice. Is it true that John is nice?', True],
  [1334, 'John is nice. Is it false that John is nice?', False],

  # -- who-is identity questions --

  [1335, 'John Sweeney is a car. John Smith is bad. Who is John Sweeney?', 'A car.'],

  [1336, 'John Sweeney is a car. Who is John?', ['John Sweeney is a car.', 'A car.', 'John Sweeney.']],

  [1339, 'John Sweeney is cool and bought a car. John is a bad baby man. John is not big. Who is John?', ['John Sweeney is a not big cool bad baby man.', 'John Sweeney.', 'A cool baby man.', 'A cool baby and a man.']],

  # -- what/who/whom-of questions --

  [1340, 'Ellen is afraid of John. What is Ellen afraid of?', 'John'],
  [1341, 'Ellen is afraid of John. Who is Ellen afraid of?', 'John'],
  [1342, 'Ellen is afraid of John. Whom is Ellen afraid of?', 'John'],
  [1343, 'Ellen is afraid of John. Ellen is afraid of whom?', 'John'],
  [1344, 'Ellen is afraid of John. Ellen is afraid of who?', 'John'],

  [1345, 'Ellen is fond of John. Who is Ellen afraid of?', None],
  [1346, 'Ellen is fond of John. Whom is Ellen afraid of?', None],
  [1347, 'Ellen is fond of John. Ellen is afraid of who?', None],

  # -- multi-entity who/what questions --

  [1348, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man has an apple?""", 'John'],
  [1349, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which has a pear?""", 'Mike'],
  [1350, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which is bad?""", 'Greg'],
  [1351, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man has a potato?""", None],
  [1352, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man is nice?""", 'John and Mike'],
  [1353, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man is bad?""", 'Greg'],
  [1354, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has a pear?""", 'Mike'],
  [1355, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which bad man has a pear?""", None],
  [1356, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has an apple or a pear?""", 'John and Mike'],
  [1357, """John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has an apple and a pear?""", None],

  [1358, """Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which animal can fly?""", 'A squirrel'],
  [1359, """Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which animal cannot fly?""", 'A fox'],
  [1360, """Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which can fly?""", 'A squirrel'],

# == IF-THEN INFERENCE ==

  # -- basic if-then --

  [1362, 'If cars are red, elephants are nice. Cars are red. Elephants are nice?', True],
  [1363, 'If cars are red, elephants are nice. Elephants are nice?', None],
  [1364, 'If some cars are red, elephants are nice. John is a red car. Elephants are nice?', True],
  [1365, 'If cars are green, elephants are nice. If elephants are nice, squirrels are red. Cars are green. Squirrels are red?', True],
  [1366, 'If cars have roofs, elephants are nice. Cars have roofs. Elephants are nice?', True],
  [1367, 'If some cars have roofs, elephants are nice. John is a car. John has a roof. Elephants are nice?', True],
  [1368, 'If some car has a roof, elephants are nice. John is a car. John has a roof. Elephants are nice?', True],

  # -- if-then with variables --

  [1369, 'If X is cool then X is red. John is cool. Mike is red?', None],
  [1370, 'If X is cool then X is red. John is cool. John is red?', True],

  [1371, 'If X is cool and X is nice then X is red. John is nice and cool. John is red?', True],
  [1372, 'If X is cool and nice then X is red. John is nice and cool. John is red?', True],
  [1373, 'If X is cool and X is nice then X is red. Mike is nice. Mike is red?', None],

  [1374, 'If X is cool and X is nice then X is red. Mike is cool. Mike is red?', None],

  [1375, """If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike and Mary.
      Who is a child of John?""", 'Mike and Mary'],
  [1376, """If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike, Mary and Eve.
      Who is a child of John?""", 'Mike, Mary and Eve'],
  [1377, """If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike or Mary.
      Who is a child of John?""", 'Mike or Mary'],

  [1378, 'If X1 is a grandfather of Y1, Y1 is not a child of X1. John is a grandfather of Mike. Who is not a child of John?', 'Mike.'],
  [1379, 'If X1 is not a parent of Y1, Y1 is not a child of X1. John is not a parent of Mike. Who is not a child of John?', 'Mike.'],

  [1380, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John. Luke is a grandfather of Mike?""", True],
  [1381, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. Mike is a grandchild of Luke?""", True],
  [1382, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike is male. Mike is a grandson of Luke?""", True],
  [1383, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike and Mickey are male. Who is a grandson of Luke?""", 'Mike and Mickey.'],
  [1384, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike and Mickey are not female. Any person is male or female.
      Who is a grandson of Luke?""", ['Mickey and Mike.', 'Mike and Mickey.']],
  [1385, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike or Mickey is not female. Any person is male or female.
      Who is a grandson of Luke?""", 'Mike or Mickey.'],
  [1386, """If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike or Mickey are not female. Any person is male or female.
      Who is a grandson of Luke?""", 'Mike or Mickey.'],

  [1387, """If an animal is cool and defeated then it is green.
   John is a cool defeated animal.
   Mike is an animal. Mike is cool. John is green?""", True],
  [1388, """If an animal is cool and defeated then it is green.
   John is a cool defeated animal.
   Mike is an animal. Mike is cool. John is not green?""", False],
  [1389, """If an animal is cool and defeated then it is green.
   John is a defeated animal.
   Mike is an animal. Mike is cool. John is green?""", None],

  [1390, """If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals.
    John is badly defeated. John is weak?""", True],
  [1391, """If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals.
    John is badly defeated. Mike is weak?""", None],
  [1392, """If someone is a nice animal and badly defeated then they are weak. John is a nice animal.
    Mike is badly defeated. Mike is weak?""", None],

  [1393, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. John is green?""", True],
  [1394, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. Who is green?""", 'John'],
  [1395, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. John is not green?""", False],
  [1396, """If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. Mike is green?""", None],

  [1397, 'If someone is a bird and wounded then they are abnormal. John is wounded. John is a bird. John is abnormal?', True],
  [1398, 'If someone is a bird and wounded then they are abnormal. John is a bird. John is abnormal?', None],

  # -- have in if-then rules --

  [1399, """If an animal has a trunk, it is an elephant. John has a long trunk. John is an animal.
      John is an elephant?""", True],
  [1400, 'If an animal or bird has a tail, it is cute. John has a tail. John is cute?', None],
  [1401, 'If an animal or bird has a tail, it is cute. John is an animal. John has a tail. John is cute?', True],
  [1402, 'If an animal or bird has a tail, it is cute. John is a bird. John has a tail. John is cute?', True],
  [1403, 'If an animal or bird has a tail, it is cute. John is a bird or an animal. John has a tail. John is cute?', True],
  [1404, 'If a bear is nice, it has a tail. John is a nice bear. John has a tail?', True],
  [1405, 'If a big bear is nice, it has a tail. John is a nice bear. John has a tail?', None],
  [1406, 'If a bear is nice and has a trunk, it has a tail. John is a nice bear. John has a trunk. John has a tail?', True],
  [1407, 'If the bear is strong, the fox is nice. The bear is strong. Who is nice?', 'The fox.'],
  [1408, 'If the bear is strong, the fox is nice. The bear is strong. John is a fox. Who is nice?', ['The fox.', 'John.']],

  # -- coordination in conditionals --

  [1409, 'If animal or bird is nice and simple, it is cute. John is cute?', None],
  [1410, 'If animal or bird is nice and simple, it is cute. John is a nice and simple animal. John is cute?', True],
  [1411, 'If animal or bird is nice and simple, it is cute. John is a nice and simple bird. John is cute?', True],
  [1412, 'If animal or bird is nice and simple, it is cute. John is a nice animal. John is cute?', None],

  [1413, 'If a bear who is big is strong, it is nice. John is a big strong bear. John is nice?', True],
  [1414, 'If a bear who is big is strong, it is nice. John is a big bear. John is strong. John is nice?', 'Likely true'],

  [1415, 'If a bear who eats fish is strong, it is nice. John is a bear. John eats fish. John is strong. John is nice?', 'Likely true'],
  [1416, 'If a bear who eats fish is strong, it is nice. John is a bear. John eats carrots. John is strong. John is nice?', None],
  [1417, 'If a bear who eats fish is strong, it is nice. John is a bear. John eats fish. John is nice?', None],

  [1418, 'If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats strong fish. John is white. John is nice?', True],
  [1419, 'If a big bear who eats strong fish is white, it is nice. John is a bear. John eats strong fish. John is white. John is nice?', None],
  [1420, 'If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats strong fish. John is nice?', None],
  [1421, 'If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats yellow fish. John is white. John is nice?', None],

  # -- if-then with family relations --

  [1422, 'If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike. Who is a child of John?', 'Mike.'],

  [1423, 'If John is not very big, John is nice. John is big. John is nice?', None],
  [1424, 'If John is not very big, John is nice. John is very big. John is nice?', None],
  [1425, 'If a bear is not very big, it is nice. John is a big bear. John is nice?', None],
  [1426, 'If a bear is not very big, it is nice. John is a very big bear. John is nice?', None],

# == DEFAULT & DEFEASIBLE REASONING ==

  # -- basic defaults with exceptions --

  [1427, 'Penguins are birds who do not fly. Birds fly. John is a penguin. John flies?', False],
  [1428, 'Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John flies?', False],
  [1429, 'Penguins are birds who do not fly. Birds fly. John is a bird. John flies?', True],
  [1430, 'Penguins are birds. Penguins do not fly. Birds fly. John is a bird. John flies?', True],
  [1431, 'Cars are nice. Cars are not nice?', False],

  [1432, 'Red cars are not nice. Cars are nice. Cars are not nice?', False],
  [1433, 'Red cars are not nice. Cars are nice. Red cars are not nice?', True],
  [1434, 'Red cars are not nice. Cars are nice. What are nice?', ['A car.', 'Non-red cars.']],
  [1435, 'Red cars are not nice. Cars are nice. What are not nice?', 'A red car.'],

  [1436, 'Red cars do not have trunks. Cars have trunks. Cars have trunks?', True],
  [1437, 'Red cars do not have trunks. Cars have trunks. Red cars have trunks?', False],
  [1438, 'Red cars do not have trunks. Cars have trunks. Cars have a trunk?', True],
  [1439, 'Red cars do not have trunks. Cars have trunks. Red cars have a trunk?', False],

  [1440, 'Red cars do not have trunks. Cars have a trunk. Cars have a trunk?', True],
  [1441, 'Red cars do not have trunks. Cars have trunks. John is a car. John has a trunk?', True],
  [1442, 'Red cars do not have trunks. Cars have trunks. John is a red car. John has a trunk?', False],

  # -- Tweety triangle --

  [1443, 'Penguins are birds. Penguins do not fly. Birds fly. Birds fly?', True],
  [1444, 'Penguins are birds. Penguins do not fly. Birds fly. Penguins fly?', False],
  [1445, 'Penguins are birds. Penguins do not fly. Birds fly. Who flies?', 'A bird.'],
  [1446, 'Penguins are birds. Penguins do not fly. Birds fly. Who does not fly?', 'A penguin.'],
  [1447, 'Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John is a bird?', True],
  [1448, 'Penguins are birds. Penguins do not fly. Birds fly. Mike is a bird. Mike is a penguin?', ['Likely false.', 'Probably false.']],

  [1449, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    John does not fly?""", True],
  [1450, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    Mike flies?""", True],
  [1451, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    John runs?""", None],
  [1452, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who does not fly?""", 'John.'],
  [1453, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies?""", 'Mike and Eve.'],
  [1454, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who eats?""", ['John, Mike and Eve.', 'John, Mike, and Eve.', 'Mike and Eve.']],
  [1455, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies and eats?""", 'Mike and Eve.'],
  [1456, """Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies or eats?""", 'John, Mike and Eve.'],
  [1457, """Birds fly and eat. Baby birds do not fly. John is perhaps a baby.
     Mike and Eve and John are birds. Who flies and eats?""", ['Mike, Eve and likely John', 'Mike and Eve.']],

  [1458, """Bears eat berries. Baby bears do not eat berries. John is a bear.
     John eats berries?""", True],
  [1459, """Bears eat berries. Baby bears do not eat berries. John is a baby bear.
     John eats berries?""", False],
  [1460, """Bears eat berries. Baby bears eat no berries. John is a baby bear.
     John eats berries?""", False],
  [1461, """Bears eat berries. Baby bears do not eat berries. John and Mike are bears.
      John is a baby bear.
      Who eats berries?""", 'Mike.'],

  [1462, """Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds.
      Who can fly?""", 'Mike and Eve.'],
  [1463, """Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds.
      Who can not fly?""", 'John.'],
  [1464, """Bears can eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who can eat berries?""", 'Mike.'],
  [1465, """Bears can eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who can not eat berries?""", 'John.'],

  [1466, 'Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  [1467, 'Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John flies?', False],
  [1468, 'Birds can fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  [1469, 'Birds fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],
  [1470, 'Birds fly. No penguin can fly. Penguins are birds. John is a bird. John flies?', True],
  [1471, 'Birds can fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],

  [1472, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who flies?', 'Mike'],
  [1473, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who does not fly?', 'John'],
  [1474, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who can fly?', 'Mike'],
  [1475, 'Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John'],

  [1476, """Bears eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who eats berries?""", 'Mike.'],
  [1477, """Bears eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who does not eat berries?""", 'John.'],
  [1478, 'Birds can fly. Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John.'],
  [1479, """Bears can eat berries. Baby bears do not eat berries. John and Mike are bears.
      John is a baby bear.  Who can not eat berries?""", 'John.'],
  [1480, 'Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', ['Perhaps John.', 'John.']],

  [1481, 'John is a car. John is bad. Who is John?', ['John is a bad car.', 'A car.']],
  [1482, 'John is a car. John is bad. Who is John?', ['John is a bad car.', 'A car.']],

  [1483, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Mike is big?""", True],
  [1484, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. John is big?""", False],
  [1485, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Who is big?""", 'Mike.'],
  [1486, """Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Who is not big?""", 'John.'],
  [1487, """Elephants are big. Young elephants are not big.
      Who is big?""", ['An elephant.', 'Elephants that are not young.']],
  [1488, """Elephants are big. Young elephants are not big.
      Who is not big?""", 'A young elephant.'],

# == DEFAULTS WITH EXCEPTIONS (BLOCKING) ==

  # -- default do-actions --

  [1489, 'Bears eat berries. John is a bear. John eats berries?', True],
  [1490, 'Bears eat berries. John is a bear. John eats some berries?', True],
  [1491, 'Bears eat berries. John is a bear. John eats all berries?', None],
  [1492, 'Bears eat all berries. John is a bear. John eats all berries?', True],
  [1493, 'Some bears eat all berries. John is a bear. John eats berries?', None],

  [1494, 'Some bears eat all berries. Some bears eat berries?', True],

  # -- blocking in conditionals --

  [1495, """If a bear eats red berries, it is big. John eats berries. John is a bear.
     John is big?""", None],
  [1496, """If a bear eats red berries, it is big. John eats red berries. John is a bear.
     John is big?""", True],
  [1497, 'If X1 eats berries, it is a bear. John eats red berries. John is a bear?', True],

  # -- default disjunctive actions --

  [1499, 'Birds fly or swim. John is a bird. John swims?', None],
  [1502, 'Birds fly and swim. John is a bird. John swims and flies?', True],

# == UNCERTAINTY & CONFIDENCE ==

  # -- adverbial probability --

  [1503, 'Elephants are probably animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1504, 'Elephants are rarely animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1505, 'Probably elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1506, 'Probably elephants are not animals. John is an elephant. John is an animal?', 'Probably false.'],

  # -- sentence-initial probably --

  [1507, 'Probably elephants have long trunks. John is an elephant. John has a trunk?', 'Probably true.'],
  [1508, 'Probably elephants have no trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  [1509, 'Elephants have probably long trunks. John is an elephant. John has a long trunk?', 'Probably true.'],
  [1510, 'Elephants have probably no trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  [1511, 'Elephants have rarely trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  [1512, 'It is true that elephants have long grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  [1513, 'It is false that elephants have long grey trunks. John is an elephant. Who has a trunk?', None],
  [1514, 'It is probably true that elephants have long grey trunks. John is an elephant. Who has a trunk?', ['Probably John.', 'John.']],
  [1515, """It is probable that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1516, """It is probable that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably false.'],
  [1517, """It is probably true that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1518, """It is probably false that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1519, """It is unlikely that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably false.'],
  [1520, """It is unlikely that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1521, """It is probable that if X1 is not a grandfather of Y1, Y1 is a child of X1. John is not a grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  [1522, 'Tallinn is probably in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  [1523, 'Tallinn is hardly in Latvia. Tallinn is in Latvia?', 'Likely false.'],
  [1524, 'It is true that Tallinn is in Estonia. Tallinn is in Estonia?', True],
  [1525, 'It is false that Tallinn is in Latvia. Tallinn is in Latvia?', False],
  [1526, 'It is probably true that Tallinn is in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  [1527, 'It is probably false that Tallinn is in Latvia. Tallinn is in Latvia?', 'Probably false.'],
  [1528, 'Probably Tallinn is in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  [1529, 'It is not probable that Tallinn is in Latvia. Tallinn is in Latvia?', 'Probably false.'],

  # -- it is true/false that --

  [1530, 'It is true that elephants are animals. John is an elephant. John is an animal?', True],
  [1531, 'It is false that elephants are animals. John is an elephant. John is an animal?', False],
  [1532, 'It is not true that elephants are animals. John is an elephant. John is an animal?', False],
  [1533, 'It is not false that elephants are animals. John is an elephant. John is an animal?', True],
  [1534, 'It is probably true that elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1535, 'It is probably false that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1536, 'It is probable that elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  [1537, 'It is not probable that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1538, 'It is unlikely that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  [1539, 'It is true that John is a child of Mike. John is a child of Mike?', True],
  [1540, 'It is false that John is a child of Mike. John is a child of Mike?', False],

  # -- it is probable/improbable that --

  [1541, 'It is probable that John is a child of Mike. John is a child of Mike?', 'Probably true.'],
  [1542, 'It is probably true that John is a child of Mike. John is a child of Mike?', 'Probably true.'],
  [1543, 'It is improbable that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1544, 'It is not probable that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1545, 'It is unlikely that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1546, 'It is probably false that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  [1547, 'John is probably a child of Mike. John is a child of Mike?', 'Probably true.'],
  [1548, 'Probably John is a child of Mike. John is a child of Mike?', 'Probably true.'],

  # -- negated universals --

  [1549, 'It is not true that all big yellow cats are strong. Some yellow cats are not strong?', True],
  [1550, 'It is not true that all big yellow cats are strong. Some red cats are not strong?', None],

  [1552, 'John is nice. It is true that John is nice?', True],
  [1553, 'John smokes tobacco with a probability 0.8. What does John smoke?', ['Likely a tobacco', 'Tobacco.']],
  [1554, 'John smokes tobacco with a probability 0.8. John smokes?', 'Likely true'],
  [1555, 'John smokes tobacco with a probability 80 percent. Does John smoke?', 'Likely true'],
  [1556, 'John is a man. John is probably not bad. Who is John?', ['John is a not bad man.', 'A man.']],
  [1557, """Birds fly and eat. Baby birds do not fly. John is hardly a baby bird.
     Mike and Eve and John are birds. Who flies and eats?""", ['Mike, Eve and John', 'Mike, Eve, and John.']],
  [1558, """Birds fly and eat. Baby birds do not fly. John is probably a baby bird.
     Mike and Eve and John are birds. Who flies and eats?""", 'Mike and Eve'],

  # -- explicit percentage probability --

  [1559, 'John is an elephant with a probability 100 percent. John is an elephant?', True],
  [1560, 'John is an elephant with a probability 0 percent. John is an elephant?', False],
  [1561, 'John is an elephant with a probability 10 percent. John is an elephant?', 'Likely false.'],
  [1562, 'John is an elephant with a probability 90 percent . John is an elephant?', 'Likely true.'],
  [1563, 'John is an elephant with a probability 50 percent. John is an elephant?', None],

  [1564, 'Tallinn is in Estonia with a probability 90 percent. Tallinn is in Estonia?', 'Likely true.'],
  [1565, 'Tallinn is in Latvia with a probability 10 percent. Tallinn is in Latvia?', 'Likely false.'],
  [1566, 'Tallinn is in Latvia with a probability 50 percent. Tallinn is in Latvia?', None],

  [1567, 'Elephants have a trunk with a probability 90 percent. John is an elephant. John has a trunk?', 'Likely true.'],
  [1568, 'Elephants have a trunk with a probability 10 percent. John is an elephant. John has a trunk?', 'Likely false.'],
  [1569, 'Elephants have a trunk with a probability 50 percent. John is an elephant. John has a trunk?', None],
  [1570, 'Elephants have a trunk with a probability 90 percent. John is an elephant. Who has a trunk?', ['Likely John.', 'John.']],

  [1571, 'Elephants probably do not have wings. John is an elephant. Who does not have wings?', ['Probably John.', 'John.']],
  [1572, 'Elephants probably do not have wings. John is maybe an elephant. Who does not have wings?', 'Maybe John.'],
  [1573, 'John probably smokes. John smokes?', 'Probably true'],
  [1574, 'Probably John smokes. John smokes?', 'Probably true'],
  [1575, 'It is probably true that John smokes. John smokes?', 'Probably true'],

  # -- explicit decimal probability --

  [1576, 'John smokes with a probability 90%. John smokes?', 'Likely true'],
  [1577, 'John smokes with a probability 90 percent. John smokes?', 'Likely true'],
  [1578, 'John smokes with a probability 0.9. John smokes?', 'Likely true'],
  [1579, 'John smokes with a probability 0.1. John smokes?', 'Likely false'],
  [1580, 'John smokes tobacco with a probability 0.8. John smokes what?', ['Likely a tobacco', 'Tobacco.']],

  # -- probability with location --

  [1581, 'Probably John is in a cave. Where is John?', ['Probably in the cave', 'Probably in a cave.']],
  [1582, 'John is probably in a cave. Where is John?', ['Probably in the cave', 'Probably in a cave.', 'In a cave.']],

  [1583, 'John is in a cave with a probability 90%. Where is John?', 'Likely in the cave'],
  [1584, 'John is in a cave with a probability 10%. Where is John?', None],
  [1585, 'John is in a cave with a probability 10%. John is in the cave?', 'Likely false'],
  [1586, 'John is in a cave with a probability 10%. John is in a cave?', 'Likely false'],

# == ADVANCED SEMANTIC OPERATORS ==

  # -- implicative: manage --

  [1587, 'John managed to open the door. John opened the door?', True],
  [1588, 'John managed to open the door. John did not open the door?', False],
  [1589, 'Mary managed to solve the puzzle. Mary solved the puzzle?', True],

  # -- implicative: fail --

  [1590, 'Tom failed to catch the bus. Tom caught the bus?', False],
  [1591, 'Eve failed to finish the report. Eve finished the report?', False],

  # -- non-implicative: try --

  [1592, 'John tried to open the door. John opened the door?', None],
  [1593, 'Mary tried to solve the puzzle. Mary solved the puzzle?', None],

  # -- non-implicative: want --

  [1594, 'Tom wanted to leave. Tom left?', None],

  # -- promise --

  [1595, 'John promised to help Mary. John helped Mary?', None],

  # -- decide --

  [1596, 'Mary decided to leave. Mary left?', None],

  # -- refuse --

  [1597, 'Tom refused to eat the soup. Tom ate the soup?', False],
  [1598, 'Tom refused to eat the soup. Did Tom drink the soup?', None],

  # -- forget --

  [1599, 'Eve forgot to lock the door. Eve locked the door?', False],

  # -- raising: seem/appear --

  [1600, 'John seemed tired. John was energetic?', None],

  # -- passive raising --

  [1601, 'John was seen to enter the room. John entered the room?', True],
  [1602, 'John was seen to enter the room. Did John leave the room?', None],
  [1603, 'Mary was heard to sing. Mary sang?', True],

  # -- deontic modality --

  [1604, 'You may enter the building. Do you have permission to enter?', True],

  # -- focus particle: only --

  [1605, 'Only John bought a car. Did Mary buy a car?', False],
  [1606, 'Only John bought a car. Who bought a car?', 'John.'],
  [1607, 'John only eats apples. Does John eat bananas?', False],

  # -- exceptive --

  [1608, 'Everyone except John arrived. Did John arrive?', False],
  [1609, 'All the boxes are red except for the small one. Is the small box red?', False],

  # -- embedded interrogative --

  [1611, 'Mary asked whether it was raining. Does Mary know if it is raining?', None],

  # -- donkey anaphora --


  # -- degree complement: too --


  # -- causative --

  [1615, 'John made Mary cry. Did Mary cry?', True],
  [1616, 'Tom had the mechanic fix his car. Who fixed the car?', 'The mechanic.'],

  # -- cleft sentence --

  [1617, 'It was John who ate the cake. Who ate the cake?', 'John.'],

# == COMPLEX REASONING CHAINS ==

  # -- fear chains --

  [1619, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is emily afraid of?', ['A wolf.', 'wolf', 'Wolves.', 'wolves']],
  [1620, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is winona afraid of?', ['A mouse.', 'mouse', 'Mice.', 'mice']],
  [1621, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is gertrude afraid of?', ['mouse', 'Jessica.']],
  [1622, 'Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is jessica afraid of?', ['A cat.', 'cat', 'Cats.', 'cats']],

  # -- extended fear chains --

  [1623, 'Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is emily afraid of?', 'sheep'],
  [1624, 'Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is jessica afraid of?', ['A cat.', 'cat', 'Cats.', 'cats']],
  [1625, 'Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is gertrude afraid of?', ['A wolf.', 'wolf', 'Wolves.', 'wolves']],

  [1626, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Emily afraid of?""", ['Probably a wolf', 'Wolves.', 'Gertrude.']],
  [1627, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    Who is Emily afraid of?""", ['Probably Gertrude', 'Gertrude.', 'Wolves.']],
  [1628, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What are cats afraid of?""", ['A wolf.', 'wolf', 'Wolves.', 'wolves']],
  [1629, """Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Winona afraid of?""", ['A mouse.', 'mouse', 'Mice.', 'mice']],




]
