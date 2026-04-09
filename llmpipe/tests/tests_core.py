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

  ['Elephants are animals. Elephants are animals?', True],
  ['Elephants are animals. John is an elephant. John is an animal?', True],
  ['Elephants are not birds. John is an elephant. John is not a bird?', True],
  ['Elephants are animals. John is an elephant. Who is an animal?', 'John.'],
  ['Elephants are not birds. John is an elephant. John is a bird?', False],
  ['Elephants are animals. Who is an animal?', 'An elephant.'],
  ['Elephants are grey animals. John is an elephant. Who is grey?', 'John.'],
  ['Elephants are big animals. John is an elephant. Who is nice?', None],

# == LOGICAL CONNECTIVES ==

  ['John is a man or not a man?', True],
  ['John is a man and not a man?', False],
  ['John is tall or not tall?', True],
  ['John is tall and not tall?', False],
  ['John is a tall man and not a tall man?', False],
  ['John is a tall man or not a tall man?', True],
  ['John has a car or does not have a car?', True],
  ['John has a car and does not have a car?', False],
  ['John has a car?', None],
  ['John is in Estonia or is not in Estonia?', True],
  ['John is in Estonia and is not in Estonia?', False],
  ['John is in Estonia?', None],

# == PROPERTIES & ADJECTIVAL LOGIC ==

  # -- adjective combos with and/or --

  ['Big or strong elephants are nice. John is a big elephant. John is nice?', True],
  ['Big or strong elephants are nice. John is a big elephant. John is strong. John is nice?', True],
  ['Big or strong elephants are nice. John is an elephant. John is nice?', None],
  ['Big and strong elephants are nice. John is a big elephant. John is a strong elephant. John is nice?', True],
  ['Yellow and green elephants are nice. John is an elephant. John is yellow and green. John is nice?', "Probably true."],
  ['Big and strong elephants are nice. John is a strong elephant. John is nice?', None],
  ['Big and not strong elephants are nice. John is a big elephant. John is a not strong elephant. John is nice?', True],

  # -- degree modifiers: very, somewhat, extremely --

  ['John is very big. John is extremely big?', True],
  ['John is very big. John is very big?', True],
  ['John is very big. John is big?', True],

  ['John is big. John is very big?', None],
  ['John is big. John is big?', True],
  ['John is somewhat big. John is big?', True],
  ['John is somewhat big. John is somewhat big?', True],
  ['John is somewhat big. Mike is very big. Who is very big?', 'Mike'],
  ['John is big. John is not big?', False],
  ['John is very big. John is not very big?', False],
  ['John is very big. John is not big?', False],
  ['John is somewhat big. John is not somewhat big?', False],
  ['John is somewhat big. John is not big?', False],
  ['John is not very big. John is very big?', False],
  ['A not very big bear is nice. The bear is a very big bear?', False],
  ['A not very big bear is nice. The bear is a somewhat big bear?', None],
  ['John is a not very big bear. John is a very big bear?', False],
  ['John is not a very big bear. John is a very big bear?', False],

  ['A very big mouse is nice. The mouse is a very big mouse?', True],
  ['A very big mouse is nice. The mouse is a big mouse?', True],
  ['A very big mouse is nice. The mouse is very big?', True],
  ['A very big mouse is nice. The mouse is big?', True],

  # -- class-relative properties --

  ['Frogs are small animals. John is a frog. John is a small animal?', True],
  ['Frogs are small animals. John is a frog. John is small?', True],
  ['Frogs are small. John is a frog. John is small?', True],
  ['Frogs are small. John is a frog. John is a small animal?', None],
  ['Frogs are small. Frogs are animals. John is a frog. John is a small animal?', 'Likely true'],

  ['John is a big mouse. John is big?', True],
  ['John is a big mouse. John is a big mouse?', True],
  ['John is a big mouse. John is a big thing?', None],

  ['The car is red. The car is red?', True],
  ['The car is red. The car is nice?', None],
  [' The big mouse is strong. The mouse is a big mouse?', True],

# == NUMBER & PLURALITY ==

  # -- conjunction in have-objects --

  ['Elephants have long trunks and short tails. John is an elephant. Who has a trunk and a tail?', 'John.'],
  ['Elephants have long trunks and short tails. John is an elephant. Who has a long trunk and a short tail?', 'John.'],

  ['Elephants have long trunks and no wings. John is an elephant. John has a wing?', False],
  ['Elephants have long trunks and no wings. John is an elephant. John has no wing?', True],
  ['Elephants have long trunks and no wings. John is an elephant. John does not have a wing?', True],
  ['Elephants have long trunks and no wings. John is an elephant. Who does not have a wing?', ['John.', 'Elephants.']],
  ['Elephants have long trunks and no wings. John is an elephant. John has a long trunk and no wing?', True],

  # -- disjunction in have-objects --

  ['Elephants have trunks or tails. John is an elephant. John has no trunk. John has a tail?', True],
  ['Elephants have either trunks or tails. John is an elephant. John has a tail and a trunk?', False],
  ['Elephants have trunks or tails. John is an elephant. John has a tail or a trunk?', True],

  ['Elephants have long or short trunks. John is an elephant. John does not have a long trunk. John has a short trunk?', True],
  ['Elephants have long or short trunks. John is an elephant. John has a trunk?', True],
  ['Elephants have long or short trunks. John is an elephant. John has a long trunk?', None],

# == COREFERENCE & ANAPHORA ==

  # -- basic property assertions --

  ['John was yellow. John was yellow?', True],
  ['John was yellow. John was nice?', None],
  ['John was yellow. A man was nice?', None],

  ['A man was yellow. A man was yellow?', True],
  ['A man was yellow. A man was nice?', None],
  ['A man was yellow. John was nice?', None],

  # -- definite descriptions --


  # -- definite description resolution --

  ['An elephant was strong. An animal lifted a stone. Who lifted the stone?', 'The animal'],
  ['An elephant was strong. The nice animal lifted a stone. Who lifted the stone?', ['The nice animal', 'The elephant.']],
  ['An elephant was strong. The animal lifted a stone. Who lifted the stone?', 'The elephant'],
  ['A nice elephant was strong. The nice animal lifted a stone. Who lifted the stone?', 'The nice elephant'],
  ['A nice elephant was strong. A mouse was white. The white animal lifted the stone. Who lifted the stone?', 'The mouse'],
  ['A nice elephant was strong. A flower was white. The animal lifted the stone. Who lifted the stone?', ['The nice elephant', 'The elephant.', 'The animal.']],
  ['An old nice grey elephant was strong. The nice animal lifted a stone. Who lifted the stone?', ['The old nice grey elephant', 'The elephant.']],

  ['A big old grey elephant was strong. The big animal lifted a stone. The stone was red. The old animal lifted a red stone?', True],
  ['A big old grey elephant was strong. The big animal lifted a stone. The stone was heavy. The old animal lifted a heavy stone?', True],
  ['A big old grey elephant was strong. The big animal lifted a stone. It was red. The grey animal lifted what?', ['The stone', 'A red stone.']],

  # -- determiners: a/the --


  # -- distinct indefinites --

  ['A red car is big. A new car is small. A car is old?', None],
  ['A red car is big. A new car is nice. A car is red and big?', True],
  ['A red car is big. A new car is nice. A car is red and nice?', None],
  ['A red car is big. A new car is nice. The car is red?', None],
  ['A red car is big. A new car is nice. The red car is big?', True],
  ['A red car is big. A new car is nice. The new car is nice?', True],

  ['A red car is big. The red car is strong. The car is red and strong?', True],
  ['A red car is big. The car is strong. The car is red and strong?', True],
  ['A red car is big. The car is strong. A car is black?', None],

  # -- pronoun resolution (he/she/it) --

  ['Mary saw John. She was nice. Who was nice?', 'Mary'],
  ['Mary saw John. He was nice. Who was nice?', 'John'],
  ['John saw Mary. She was nice. Who was nice?', 'Mary'],
  ['John saw Mary. He was nice. Who was nice?', 'John'],

  ['A mother saw a man. She was nice. Who was nice?', ['The mother', 'The nice mother']],
  ['A mother saw a man. He was nice. Who was nice?', ['The man', 'The nice man']],
  ['A boy saw a girl. She was nice. Who was nice?', ['The girl', 'The nice girl']],
  ['A boy saw a girl. He was nice. Who was nice?', ['The boy', 'The nice boy']],
  ['A mother saw a fox. It was nice. Who was nice?', ['The fox', 'The nice fox']],
  ['A mother saw a fox. She was nice. Who was nice?', ['The mother', 'The nice mother']],
  ['A fox saw a mother. She was nice. Who was nice?', ['The mother', 'The fox.', 'The nice mother']],
  ['A mother saw a fox. He was nice. Who was nice?', ['The fox', 'The nice fox']],
  ['A fox saw a mother. He was nice. Who was nice?', ['The fox', 'The nice fox']],
  ['A fox saw a mother. It was nice. Who was nice?', ['The fox', 'The mother.', 'The nice mother']],

  # -- names and non-names --

  ['Muggles cannot disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?', False],
  ['Muggles can not disappear. Mr Dursley is a Muggle. Mr Dursley can disappear?', False],
  ['Americans cannot disappear. Mr Dursley is an American. Mr Dursley can disappear?', False],
  ['Americans can not disappear. Mr Dursley is an American. Mr Dursley can disappear?', False],
  ['Catholics can not disappear. Mr Dursley is a catholic. Mr Dursley can disappear?', False],

  # -- true as adjective vs truth value --

  ['Sue is a true patriot. Sue is a true patriot?', True],
  ['Sue is a true patriot. Sue is a nice patriot?', None],
  ['Sue is a true patriot. Sue is a true driver?', None],

  ['The elephants saw a fox. They were nice. The elephants were nice?', True],
  ['The elephants saw a fox. They were nice. The fox was nice?', None],
  ['The elephants saw a fox. They were nice. Who were nice?', 'The elephants'],
  ['The elephants saw a fox. It was nice.  The fox was nice?', True],
  ['The elephants saw a fox. It was nice.  The elephants were nice?', None],

  ['The fox saw the elephants. They were nice. The elephants were nice?', True],
  ['The fox saw the elephants. They were nice. The fox was nice?', None],
  ['The fox saw the elephants. It was nice.  The elephants were nice?', None],

  # -- she/he pronoun resolution --

  ['Mary was in a room. She was in the room?', True],
  ['Mary was in a room. She was in a room?', True],
  ['Mary was in a room. She was not in the room?', False],
  ['Mary was in a room. She was not in a room?', False],
  ['She was in a room. She was in the room?', True],

  ['An apple was bad. She was in a room. She was in the room?', True],
  ['An apple was bad and she was in a room. She was in the room?', True],
  ['An apple was bad. She was in a room. An apple was in a room?', None],
  ['An apple was bad and she was in a room. An apple was in a room?', None],

  ['John was bad. She was in a room. John was in a room?', None],
  ['She was in a room. Who was in the room?', 'She'],

  # -- these/they anaphora --

  ['The aunts saw shoes. These were nice. What was nice?', 'The shoes'],
  ['The foxes saw aunts. They were nice. What was nice?', ['The aunts', 'The foxes.']],
  ['A car had a dent. This was deep. What was deep?', 'A dent'],
  ['A car had a dent. It was fast. What was fast?', 'The car'],

  # -- definite/indefinite coreference --

  ['A gray elephant was nice. A white elephant was nice. The elephant was cool. The white elephant was cool?', True],
  ['A gray elephant was nice. A white elephant was nice. The elephant was cool. The gray elephant was cool?', None],
  ['A gray elephant was nice. A white elephant was nice. It was cool. The white elephant was cool?', True],
  ['A gray elephant was nice. A white elephant was nice. It was cool. The gray elephant was cool?', None],

  # -- pronouns, reflexives, reciprocals --


  ['Mike ate berries in the forest bought by Mary. Mike ate berries in the forest bought by Mary?', True],
  ['Mike ate berries in the forest bought by Mary. Mike ate berries in the forest bought by John?', None],
  ['Bears ate berries in the forest bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  ['Bears ate berries in the forest bought by Mary. Bears ate berries in the forest bought by John?', None],

  # -- reflexives --

  ['John saw himself in the mirror. Who did John see?', ['John.', 'Himself.']],
  ['John saw himself in the mirror. Did Mary see John in the mirror?', None],
  ['The boy lost his backpack. Who does the backpack belong to?', 'The boy.'],
  ['The boy lost his backpack. Did the boy find his backpack?', None],
  ['The students brought their books. Whose books were they?', ["The students'.", 'The students.']],
  ['John saw himself in the mirror. John saw John?', True],
  ['John saw himself in the mirror. Did John see Mary?', None],
  ['Mary blamed herself. Mary blamed Mary?', True],
  ['Tom washed himself. Tom washed Tom?', True],
  ['Tom washed himself. Did Tom wash Mary?', None],
  ['Eve introduced herself. Eve introduced Eve?', True],

  # -- reciprocals --

  ['John and Mary saw each other. John saw Mary?', True],
  ['John and Mary saw each other. Mary saw John?', True],
  ['John and Mary saw each other. Did John see Eve?', None],

  ['Tom and Eve greeted each other. Tom greeted Eve?', True],
  ['Tom and Eve greeted each other. Eve greeted Tom?', True],
  ['Tom and Eve greeted each other. Did Tom greet Mary?', None],

  ['The boys helped themselves. The boys helped the boys?', True],
  ['The girls admired themselves. The girls admired the girls?', True],


# == POSSESSION & HAVE ==

  # -- basic have --

  ['Elephants have trunks. Elephants have trunks?', True],
  ['No elephant has wings. No elephant has wings?', True],

  ['No elephants have wings. Some elephant has wings?', False],
  ['Elephants have no wings. Some elephant has wings?', False],
  ['Elephants have no wings. John has no wings?', None],

  # -- have with quantifiers and negation --

  ['All elephants have no wings. Some elephant has wings?', False],
  ['All elephants have no wings. John has no wings?', None],
  ['Some elephants have no wings. Some elephant has wings?', None],
  ['Some elephants have no wings. John has no wings?', None],
  ['No elephants have wings. All elephants do not have wings?', True],

  ['Elephants have trunks. John has a trunk?', None],
  ['All elephants have trunks. John has a trunk?', None],
  ['Some elephants have trunks. John has a trunk?', None],

  ['Elephants have a trunk. Birds have a trunk?', None],
  ['Elephants have a trunk. Birds do not have a trunk?', None],

  # -- have with adjective-modified objects --

  ['Elephants have long trunks. John is an elephant. John has a trunk?', True],
  ['Elephants have no trunks. John is an elephant. John has a trunk?', False],

  ['Elephants have long grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  ['Elephants have long and grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  ['Elephants have long grey trunks. John is an elephant. Who has a grey trunk?', 'John.'],
  ['Elephants have long and grey trunks. John is an elephant. Who has a grey trunk?', 'John.'],
  ['Elephants have long grey trunks. John is an elephant. Who has a long red trunk?', None],

  ['Elephants have no long red trunks. John is an elephant. John has a long red trunk?', False],
  ['Elephants have no long red trunks. John is an elephant. John has a long trunk?', None],

  # -- have with negated adjectives --

  [' Elephants have not red trunks. John is an elephant. John has a not red trunk?', True],
  [' Elephants have not red trunks. John is an elephant. John has a trunk?', True],
  [' Elephants have not red trunks. John is an elephant. John has a big trunk?', None],

  [' Elephants have long not red trunks. John is an elephant. John has a long not red trunk?', True],
  [' Elephants have long not red trunks. John is an elephant. John has a long trunk?', True],
  [' Elephants have long not red trunks. John is an elephant. John has a long black trunk?', None],
  [' Elephants have long not red trunks. John is an elephant. John has a not red trunk?', True],

  [' Elephants have long not big trunks. John is an elephant. John has a long not big trunk?', True],
  [' Elephants have long not big trunks. John is an elephant. John has a not big trunk?', True],
  [' Elephants have long not red trunks. John is an elephant. John has a long not small trunk?', None],
  [' Elephants have long not big trunks. John is an elephant. John has a long trunk?', True],

  # -- do not have --

  ['Elephants do not have long red trunks. John is an elephant. John has a long red trunk?', False],
  ['Elephants do not have wings. John is an elephant. John has wings?', False],
  ['Elephants do not have wings. John is an elephant. John has a wing?', False],
  ['Elephants do not have long red wings. John is an elephant. John has a wing?', None],
  ['John has cars. John has cars?', True],
  ['John has blue cars. John has a car?', True],
  ['John has blue cars. John has a blue car?', True],
  ['Animals have legs. Animal has a leg?', True],

  ['Elephants have long trunks. John is an elephant. Who has a trunk?', 'John.'],

# == DEFINITE DESCRIPTIONS: X OF Y AND POSSESSIVES ==

  # -- X of Y in instrument phrases --

  ['John ate berries with the edge of a spoon. John ate berries with the edge of a spoon?', True],
  ['John ate berries with an edge of a spoon. John ate berries with an edge of a spoon?', True],
  ['John ate berries with the edge of a spoon. John ate berries with the edge of a fork?', None],
  ['John ate berries with the edge of a spoon. John ate berries with the tip of a spoon?', None],
  ['John ate berries with an edge of a spoon. John ate berries with an edge?', True],
  ['John ate berries with an edge of a spoon. John ate berries with a tip?', None],
  ['John ate berries with an edge of a spoon. A spoon had an edge?', True],
  ['John ate berries with an edge of a spoon. The spoon had the edge?', True],
  ['John ate berries with the edge of the spoon. The spoon had the edge?', True],
  ['John ate berries with the edge of the spoon. The spoon had the tip?', None],
  ['John ate berries with the edge of a spoon. Berries have an edge?', None],

  # -- possessive 's constructions --

  ["John's brother has a car. John's brother has a car?", True],
  ["John's brother has a car. John's sister has a car?", None],
  ["Mary's sister owns a house. Who owns a house?", "Mary's sister."],
  ["John's brother's car is red. John's brother has a car?", True],
  ["John's brother's car is red. John's brother's car is blue?", False],
  ["Mary's uncle's bicycle is blue. Mary's uncle has a bicycle?", True],
  ["Mary's uncle's bicycle is blue. Mary's aunt has a bicycle?", None],

  # -- nested possessives --

  ["The roof of John's house is green. John has a house?", True],
  ["The handle of Mary's suitcase broke. Mary had a suitcase?", True],
  ["The handle of Mary's suitcase broke. Did the suitcase break?", None],

  # -- chained of-possessives --

  ['The door of the house of John was open. John had a house?', True],
  ['The door of the house of John was open. Was the door closed?', False],
  ['The tail of the dog of Mary was short. Mary had a dog?', True],
  ["The color of John's car was black. John had a car?", True],
  ["The color of John's car was black. John had a truck?", None],
  ['The owner of the horse of Mike smiled. Mike had a horse?', True],
  ['The brother of the friend of Eve arrived. Eve had a friend?', True],
  ["The brother of the friend of Eve arrived. Did Eve's friend arrive?", None],
  ["John saw the mother of the boy. John saw a boy's mother?", True],
  ["John's sister laughed. Who has a sister?", 'John.'],
  ["John's sister laughed. Did John's brother laugh?", None],
  ["Mary's uncle arrived. Who has an uncle?", 'Mary.'],
  ['The bicycle of Tom was new. Who had a bicycle?', 'Tom.'],
  ['The bicycle of Tom was new. Was the bicycle old?', False],
  ['The toy of the child was broken. Who had a toy?', ['The child.', 'A child.']],
  ['The toy of the child was broken. Was the toy intact?', False],
  ['John does not eat a carrot. John does not eat a carrot?', True],
  ['John does not eat a carrot. John eats a carrot?', False],
  ['John is not in a cave. John is not in a cave?', True],

# == POSSESSION INFERENCE FROM DESCRIPTIONS ==

  # -- the X of Y: property queries --

  ['The head of Mary is clean. The head of Mary is clean?', True],
  ['The head of Mary is clean. A head of Mary is clean?', True],
  ['The head of Mary is clean. A head of Mike is clean?', None],
  ['The head of Mary is clean. The head is clean?', True],

  ['The car of Mary is clean. The car of Mike is clean?', None],

  ['A leg of Mary is clean. A leg of Mary is clean?', True],
  ['A leg of Mary is clean. A leg of Mary is long?', None],
  ['A leg of Mary is clean. A leg of Mike is clean?', None],

  ["Mary's head is clean. Mary's head is clean?", True],
  ["Mary's head is clean. A head of Mary is clean?", True],
  ["Mary's head is clean. A head of Mike is clean?", None],
  ["Mary's head is clean. The head is clean?", True],

  ["Mary's leg is clean. A leg of Mary is clean?", True],
  ["Mary's leg is clean. A leg of Mary is long?", None],
  ["Mary's leg is clean. A leg of Mike is clean?", None],

  # -- possessive -> have inference --

  ["Mary's car is clean. Mary has a car?", True],
  ["Mary's car is clean. Mary has a clean car?", True],
  ["Mary's car is clean. Mary has a red car?", None],
  ["Mary's car is clean. Mary has a clean bike?", None],

  ["Elephant's head is green. John is an elephant. John has a head. John has a green head?", True],
  ["Big elephant's head is green. John is a big elephant. John has a head. John has a green head?", True],
  ["Big elephant's head is green. John is an elephant. John has a head. John has a green head?", None],
  ['A head of an elephant is green. An elephant has a green head?', 'Maybe true'],

  ['A head of an elephant is green. All elephants have a head. An elephant has a green head?', True],
  ['A head of an elephant is green. Elephants have a head. An elephant has a green head?', True],
  ['A head of an elephant is green. Elephants have a head. John is an elephant. John has a green head?', True],

  # -- generic possessives --

  ["Elephant's head is green. Elephant's head is green?", 'Maybe true'],
  ['The head of Mary is clean. Mary has a clean head?', True],

  ['The car of Mary is clean. Mary has a car?', True],
  ['The car of Mary is clean. Mike has a car?', None],
  ['The car of Mary is clean. Mary has a clean car?', True],
  ['The car of Mary is clean. Mary has a red car?', None],
  ['The car of Mary is clean. Mary has a clean bike?', None],

  # -- saw X of Y --

  ['John saw the head of Mary. John saw the head of Mary?', True],
  ['John saw the head of Mary. John saw a head of Mary?', True],
  ['John saw the head of Mary. John saw the head of Mike?', None],
  ['John saw the head of Mary. John saw a head?', True],
  ['John saw the head of Mary. John saw the hands of Mary?', None],

  ['John saw the car of Mary. Mary had a car?', True],

  ['John saw the head of the elephant. John saw the head of the elephant?', True],
  ['John saw the head of the elephant. John saw the head?', True],
  ['John saw the head of the elephant. John saw a head?', True],
  ['John saw the head of the elephant. John saw the tail of the elephant?', None],
  ['John saw the head of the elephant. John saw a nice head?', None],
  ['John saw a head of an elephant. John saw a head of an elephant?', True],
  ['John saw a head of an elephant. John saw the head of the elephant?', None],
  ['John saw a head of an elephant. John saw the head?', True],
  ['John saw a head of an elephant. John saw a head?', True],
  ['John saw a head of an elephant. John saw the tail of the elephant?', None],
  ['John saw a head of an elephant. John saw a tail of an elephant?', None],
  ['John saw a head of an elephant. John saw a nice head?', None],

  # -- saw possessive-'s --

  ["John saw Mary's head. John saw Mary's head?", True],
  ["John saw Mary's head. John saw a head of Mary?", True],
  ["John saw Mary's head. John saw Mike's head?", None],
  ["John saw Mary's head. John saw the head of Mike?", None],
  ["John saw Mary's head. John saw a head?", True],
  ["John saw Mary's head. John saw the hands of Mary?", None],

  ["John saw Mary's car. Mary had a car?", True],

  ["John saw Mary's clean car. Mary had a clean car?", True],
  ["John saw Mary's clean car. Mary had a red car?", None],
  ["John saw Mary's clean car. Mary had a clean bike?", None],

  # -- saw generic possessives --

  ["John saw elephant's head. John saw elephant's head?", True],
  ["John saw elephant's head. John saw the head?", True],
  ["John saw elephant's head. John saw a head of an elephant?", True],
  ["John saw elephant's head. John saw a head of a tiger?", None],
  ["John saw elephant's head. John saw a head?", True],
  ["John saw elephant's head. John saw the tail of the elephant?", None],
  ["John saw elephant's head. John saw a nice head?", None],

  # -- a-vs-the in of-phrases --

  ['John saw a head of an elephant. John saw a head of the elephant?', True],
  ['John saw a head of the elephant. John saw a head of the elephant?', True],
  ['John saw a head of the elephant. John saw a head of an elephant?', True],
  ['John saw a head of an elephant. John saw a head of the bear?', None],
  ['John saw a head of an elephant. John saw a head of a bear?', None],
  ['John saw a head of the elephant. John saw a head of the bear?', None],
  ['John saw a head of the elephant. John saw a head of a bear?', None],
  ['John saw a head of an elephant. John saw a tail of the elephant?', None],
  ['John saw a head of the elephant. John saw a tail of the elephant?', None],
  ['John saw a head of the elephant. John saw a tail of an elephant?', None],

  ['John saw a twig of an elephant. The elephant had a twig?', True],
  ['John saw a twig of an elephant. The elephant had a spoon?', None],
  ['John saw a twig of an elephant. An elephant had a twig?', True],
  ['John saw a twig of an elephant. An elephant had a spoon?', None],
  ['John saw the twig of an elephant. The elephant had a twig?', True],

  # -- observation implies possession --

  ['John saw the twig of an elephant. The elephant had the twig?', True],
  ['John saw the twig of an elephant. The elephant had a spoon?', None],

  # -- colored X of colored Y --

  ['John saw a blue head of a red elephant. John saw a blue head of a red elephant?', True],
  ['John saw a blue head of a red elephant. John saw a blue head?', True],
  ['John saw a blue head of a red elephant. John saw the blue head?', True],
  ['John saw a blue head of a red elephant. John saw the head?', True],
  ['John saw a blue head of a red elephant. John saw a blue tail?', None],
  ['John saw a blue head of a red elephant. John saw a head of an elephant?', True],
  ['John saw a blue head of a red elephant. John saw a head of the red elephant?', True],

  # -- of-phrases in event descriptions --

  ['The hand of a man moved a wheel. The hand of a man moved a wheel?', True],
  ['The hand of a man moved a wheel. The man had a hand?', True],
  ['The hand of a man moved a wheel. A man had a hand?', True],
  ['The hand of a man moved a wheel. A man had a wheel?', None],

  # -- complex of-chains in events --

  ['A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand of a man moved a wheel of a large wheelbarrow?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand of an elephant moved a wheel of a large wheelbarrow?', None],
  ['The blue hand of a man moved a wheel of the large wheelbarrow. A blue hand of a man moved a wheel of a large wheelbarrow?', True],
  ['The blue hand of a man moved the wheel of the large wheelbarrow. The blue hand of a man moved the wheel of the large wheelbarrow?', True],
  ['The blue hand of a man moved the wheel of the large wheelbarrow. The blue hand of a man moved the large wheelbarrow?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheelbarrow?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A blue hand moved a wheel?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A right hand moved a wheel?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A leg moved a wheel?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A hand moved a wheel of a small wheelbarrow?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The man had a hand?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The man had a blue hand?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The man had a red hand?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The man had a wheel?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The wheelbarrow had a wheel?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. A large wheelbarrow had the wheel?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The large wheelbarrow had a wheel?', True],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The small wheelbarrow had a wheel?', None],
  ['A blue hand of a man moved a wheel of a large wheelbarrow. The wheelbarrow had a hand?', None],
  ['The blue hand of a man moved the wheel of the large wheelbarrow. Mary is a man?', None],
  ['The blue hand of a man moved a wheel of the large wheelbarrow. Mary is a man?', None],

  ['The hand of a man is nice. Mary is a man?', None],
  ['A hand of a man moved a wheel. Mary is a man?', None],
  ['The hand of a man moved a wheel. Mary is a man?', None],

  ['John is not in a cave. John is in a cave?', False],
  ['John does not eat a carrot. Mike eats carrots. Who eats carrots?', 'Mike'],
  ['John does not eat a carrot. Mike eats carrots. Who does not eat carrots?', 'John'],
  ['The big bear is strong. The bear is big?', True],
  [' The white mouse is strong. The mouse is white?', True],
  [' The big mouse is strong. The mouse is big?', True],

  ['The big bear is strong. The bear is strong?', True],
  ['The big bear is strong. The big bear is strong?', True],
  ['The big bear is strong. The big bear is white?', None],

# == SETS AND COUNTING ==

  # -- basic numeric have --

  ['John has three cars. John has three cars?', True],
  ['If John has three cars, John has three cars?', True],
  ['John has three nice cars. John has three nice cars?', True],

  # -- generic numeric have --

  ['Animals have two legs. Animals have two legs?', True],
  ['Animals have two legs. Animals have three legs?', False],
  ['Animals have two nice legs. Animals have two nice legs?', True],
  ['Animals have two nice legs. Animals have two long legs?', None],
  ['An animal had two legs. The animal had two legs?', True],
  ['An animal had two legs. The animal had three legs?', False],
  ['An animal had two nice legs. The animal had two nice legs?', True],
  ['An animal had two nice legs. The animal had two long legs?', None],

  # -- numeric have with relative clause --

  ['John has three cars which are nice. John has three nice cars?', True],
  ['John has three nice cars. John has three cars?', True],
  ['John has three nice cars. John has three red cars?', None],
  ['John has three nice big cars. John has three nice big cars?', True],
  ['John has three nice big cars. John has three big nice cars?', True],

  ['If John has three big nice cars, he is rich. John has three nice big cars. John is rich?', True],
  ['If John has three big nice cars, he is rich. John has three nice big cars. Who is rich?', 'John'],
  ['If John has three big nice cars, he is rich. John has three nice cars. John is rich?', None],

  ['If a person has three big nice cars, he is rich. John has three nice big cars. John is rich?', True],

  # -- numeric have: existential inference --

  ['John has three nice cars. John has a car?', True],
  ['John has three nice cars. John has a nice car?', True],
  ['An animal had two legs. The animal had legs?', True],
  ['An animal had two legs. The animal had a leg?', True],
  ['An animal had two strong legs. The animal had a strong leg?', True],
  ['John has three nice cars. John has a red car?', None],

  # -- how many questions --

  ['John has three nice cars. How many cars does John have?', 'Three'],

  ['John has one car. John has cars?', True],

# == MEASURES ==

  # -- possessive measure assertions --

  ["Nile's length is 80 kilometers. The length of Nile is 80 kilometers?", True],
  ["Nile's length is 80 kilometers. The length of Nile is 90 kilometers?", False],

  ["Car's length is 80 kilometers. The length of the car is 80 kilometers?", True],
  ["Car's length is 80 kilometers. The length of the car is 90 kilometers?", False],
  ["The car's length is 80 kilometers. The length of the car is 80 kilometers?", True],
  ["The car's length is 80 kilometers. The length of the car is 90 kilometers?", False],

  ["The red car's length is 80 kilometers. The length of the blue car is 80 kilometers?", None],
  ["The red car's length is 80 kilometers. The length of the car is 90 kilometers?", False],
  ["Emajogi's length is 80 kilometers. Emajogi's length is 80 kilometers?", True],
  ["Emajogi's length is 80 kilometers. Emajogi's length is 90 kilometers?", False],

  # -- of-phrase measure assertions --

  ['The length of Emajogi is 80 kilometers. Emajogi is 80 kilometers long?', True],
  ['The length of Emajogi is 80 kilometers. Emajogi is 90 kilometers long?', False],
  ['The nice Emajogi is 80 kilometers long. The nice Emajogi is 80 kilometers long?', True],
  ["The red car's length is 80 kilometers. What is the length of the red car?", '80 kilometers'],
  ["Emajogi's length is 80 kilometers. The length of Nile is 80 kilometers. Emajogi has the same length as Nile?", True],
  ['The nice Emajogi is 80 kilometers long. What is 80 kilometers long?', ['Emajogi', 'The nice Emajogi.']],
  ['The nice Emajogi is 80 kilometers long. The nice Emajogi is 90 kilometers long?', False],
  ['The red straw is 10 meters long. The red straw is 10 meters long?', True],
  ['The red straw is 10 meters long. The red straw is 20 meters long?', False],

  # -- has-measure assertions --

  ['John has the length 2 meters. John is 2 meters long?', True],
  ['John has the length 2 meters. John is 3 meters long?', False],
  ['John has length of 2 meters. John is 2 meters long?', True],
  ['John has length of 2 meters. John is 3 meters long?', False],
  ["John's length is 2 meters. John is 2 meters long?", True],

  # -- price assertions --

  ['The price of the red car is 2 dollars. The price of the red car is 2 dollars?', True],
  ['The price of the red car is 2 dollars. The price of the red car is 3 dollars?', False],
  ['The price of the red car is 2 dollars. The price of the red car is 2 euros?', None],

  ['The red car costs 2 dollars. The price of the red car is 2 dollars?', True],
  ['The red car costs 2 dollars. The price of the red car is 3 dollars?', False],

  ['The red car has a price of two dollars. The red car costs two dollars?', True],

  # -- has-price with word numbers --

  ['The red car has the price two dollars. The red car costs two dollars?', True],
  ['The red car has the price two dollars. The red car costs three dollars?', False],
  ['The red car has the price two dollars. The blue car costs three dollars. The red car costs 3 dollars?', False],
  ['The red car has the price two dollars. The blue car costs three dollars. The blue car costs 2 dollars?', False],
  ['The red car has the price two dollars. The blue car costs three dollars. The car costs three dollars?', True],

  ['The red car costs 2 dollars. What costs 2 dollars?', 'The red car'],

  # -- measure comparisons: below/above --

  ['The price of the car is below 20 dollars. The car costs less than 20 dollars?', True],
  ['The weight of the car is below 20 tons. The car weighs less than 20 tons?', True],
  ['The price of the car is above 20 dollars. The car costs more than 20 dollars?', True],
  ['The weight of the car is above 20 tons. The car weighs more than 20 tons?', True],
  ['The price of the car is below 20 dollars. The price of the car is 25 dollars?', False],
  ['The red car has the price two dollars. The blue car costs three dollars. The price of the red car equals the price of the blue car?', False],
  ['The red car has the price two dollars. The blue car costs three dollars. The price of the red car equals the price of the red car?', True],

  ['The red car has the price three dollars. The blue car costs three dollars. The price of the red car is the same as the price of the blue car?', True],

  # -- measure comparisons between entities --

  ['The red car has the price three dollars. The blue car costs two dollars. The price of the red car is the same as the price of the blue car?', False],
  ['The red car has the price three dollars. The blue car costs three dollars. The red car costs as much as the blue car?', True],
  ['The red car has the price three dollars. The blue car costs two dollars. The red car costs as much as the blue car?', False],
  ['The red car has the price three dollars. The blue car costs three dollars. The red car is as expensive as the blue car?', True],
  ['The red car has the price three dollars. The blue car costs two dollars. The red car is as expensive as the blue car?', False],
  ['The red car has the price three dollars. The blue car costs three dollars. The red car is as cheap as the blue car?', True],
  ['The red car has the price three dollars. The blue car costs two dollars. The red car is as cheap as the blue car?', False],
  ['The red car has the price three dollars. The blue car costs three dollars. The red car has the same price as the blue car?', True],
  ['The red car has the price three dollars. The blue car costs two dollars. The red car has the same price as the blue car?', False],
  ['The red car has the price three dollars. The blue car costs two dollars. Which car is cheaper?', 'The blue car'],

  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      Which car is longer?""", 'The black car'],
  ['The price of the car is 3 dollars. The bike is as expensive as the car. What is the price of the bike?', '3 dollars'],
  ['The red car has the price two dollars. The blue car costs three dollars. The green car costs 2 dollars. The red car costs as much as the green car?', True],

  # -- length comparisons --

  ['The length of the red car is three meters. The blue car is 2 meters long. The red car has the same length as the blue car?', False],
  ['The length of the red car is three meters. The blue car is 2 meters long. The red car does not have the same length as the blue car?', True],
  ['The length of the red car is three meters. The blue car is 3 meters long. The red car has the same length as the blue car?', True],
  ['The length of the red car is three meters. The blue car is 3 meters long. The red car does not have the same length as the blue car?', False],

  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is more than the length of the black car?""", False],
  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is less than the length of the black car?""", True],
  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is less than 2 meters?""", False],
  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is over 2 meters?""", True],
  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is more than 2 meters?""", True],
  ["""The length of the red car is 3 meters. The length of the black car is 5 meters.
      The length of the red car is under 4 meters?""", True],

  ['The length of the car is 3 meters. The bike has the same length as the car. The length of the bike is 3 meters?', True],

  # -- same-as measure equality --

  ['The price of the car is 3 dollars. The bike has the same price as the car.  The price of the bike is 3 dollars?', True],

  ['The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 3 dollars?', True],
  ['The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 2 dollars?', False],
  ['The price of the car is 3 dollars. The bike is as expensive as the car. The price of the bike is 3 drahms?', None],

  # -- as-much-as measure equality --

  ['The price of the car is 3 dollars. The bike costs as much as the car. The bike costs 3 dollars?', True],
  ['The price of the car is 3 dollars. The bike costs as much as the car. The price of the bike is less than 20 dollars?', True],
  ['The price of the car is 3 dollars. The bike costs as much as the car. The price of the bike is more than 20 dollars?', False],
  ['The price of the car is 3 dollars. The bike costs as much as the car. The bike costs less than 20 dollars?', True],
  ['The price of the car is 3 dollars. The bike costs as much as the car. The bike costs more than 20 dollars?', False],

  ['The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs less than 20 tons?', True],
  ['The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs more than 2 tons?', True],
  ['The weight of the car is 3 tons. The bike weighs as much as the car. The bike weighs more than 20 tons?', False],

  # -- what-questions on measures --

  ["Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What is 80 kilometers long?", 'Nile'],
  ["Nile's length is 80 kilometers. Amazon's length is 20 kilometers. What has the length 20 kilometers?", 'Amazon'],

  ["Car's length is 80 kilometers. Bike's length is 10 kilometers. What is 80 kilometers long?", 'A car'],
  ["Car's length is 80 kilometers. Bike's length is 10 kilometers. What has the length 10 kilometers?", 'A bike'],
  ["The car's length is 80 kilometers. The bike's length is 10 kilometers. What is 80 kilometers long?", 'The car'],
  ["The car's length is 80 kilometers. The bike's length is 10 kilometers. What has the length 10 kilometers?", 'The bike'],

  ["Emajogi's length is 80 kilometers. What is 80 kilometers long?", 'Emajogi'],
  ["Emajogi's length is 80 kilometers. What is 200 kilometers long?", None],
  ['The length of Nile is 10 meters. What has the length 10 meters?', 'Nile'],

  # -- what-is-N-long questions --

  ['Nile is 10 meters long. What is 10 meters long?', 'Nile'],
  ['Nile is 10 meters long. Emajogi is 20 meters long. The nice river is 100 meters long. What is 100 meters long?', 'The nice river'],
  ['The red straw is 10 meters long. The blue straw is 5 meters long. What is 5 meters long?', 'The blue straw'],
  ['The red straw is 10 meters long. The blue straw is 5 meters long. What is 10 meters long?', 'The red straw'],

  ['The red car has the price two dollars. The blue car costs three dollars. What costs 3 dollars?', 'The blue car'],
  ['The red car has the price two dollars. The blue car costs three dollars. What has the price 2 dollars?', 'The red car'],
  ['The red car has the price two dollars. The blue car costs three dollars. What has the price 3 dollars?', 'The blue car'],

  ['The bicycle repaired by Mike was expensive. Mike repaired the bicycle?', True],
  ['The bicycle repaired by Mike was expensive. The bicycle was expensive?', True],
  ['The bicycle repaired by Mike was expensive. The bicycle was cheap?', False],

# == QUANTIFIERS: UNIVERSAL & EXISTENTIAL ==

  # -- all implies bare plural --

  ['All elephants are animals. Elephants are animals?', True],
  ['All elephants are animals. Some elephant is an animal?', True],
  ['All elephants are animals. All elephants are animals?', 'True'],
  ['All elephants are animals. John is an animal?', None],
  ['All elephants are animals. Elephants are not animals?', False],
  ['All elephants are animals. Some elephants are not animals?', False],
  ['All elephants are animals. All elephants are not animals?', False],

  # -- some: existential --

  ['Some elephants are animals. Elephants are animals?', None],
  ['Some elephants are animals. Some elephant is an animal?', True],
  ['Some elephants are animals. All elephants are animals?', None],
  ['Some elephants are animals. John is an animal?', None],
  ['Some elephants are animals. Elephants are not animals?', False],
  ['Some elephants are animals. Some elephants are not animals?', None],
  ['Some elephants are animals. All elephants are not animals?', False],
  ['Some elephants are not animals. All elephants are animals?', False],

  # -- all-not vs not-all --

  ['All elephants are not animals. No elephant is an animal?', True],

  ['No elephant is an animal. No elephant is an animal?', True],
  ['No elephant is an animal. Some elephant is an animal?', False],

  # -- all in object position --

  ['John likes all boxers. Mike is a boxer. John likes Mike?', True],
  ['Bears eat all boxers. Mike is a boxer. Greg is a bear. Greg eats Mike?', True],
  ['Bears eat most boxers. Mike is a boxer. Greg is a bear. Bears eats Mike?', 'Probably true.'],
  ['Bears eat most boxers. Mike is a boxer. Greg is a bear. Bears eats Greg?', None],
  ['Bears eat all boxers. Mike is a boxer. Bears eat boxers?', True],
  ['Bears eat some boxers. Mike is a boxer. Bears eat Mike?', None],
  ['John likes some boxers. Mike is a boxer. John likes Mike?', None],

  ['Elephants are animals. Some elephant is an animal?', True],
  ['Elephants are animals. All elephants are animals?', True],
  ['Elephants are animals. John is an animal?', None],
  ['Elephants are animals. Elephants are not animals?', False],
  ['Elephants are animals. Some elephants are not animals?', False],
  ['Elephants are animals. All elephants are not animals?', False],

# == QUANTIFIERS: PROPORTIONAL & NUMERIC ==

  # -- distinct indefinites with quantifiers --

  ['The red square has a nail. A blue square has a hole. A square has a nail?', True],
  ['The red square has a nail. A blue square has a hole. A square has a hole?', True],
  ['The red square has a nail. A blue square has a hole. A square has a dot?', None],
  ['The red square has a nail. A blue square has a hole. A red square has a nail?', True],
  ['The red square has a nail. A blue square has a hole. A blue square has a hole?', True],
  ['The red square has a nail. A blue square has a hole. A red square has a hole?', None],

  ['The red square is nice. A blue square is cool. A square is cool?', True],
  ['The red square is nice. A blue square is cool. A square is nice?', True],
  ['The red square is nice. A blue square is cool. A square is empty?', None],

  ['Most bears are big. John is a bear. John is big?', 'Likely true.'],

# == COMPARATIVES & EQUALITY ==

  # -- basic comparatives --

  ['John is nicer than Mike. Mike is nicer than Eve. Who is nicer than Eve?', ['John and Mike.', 'John.', 'Mike.']],
  ['John is nicer than Mike. Mike is nicer than Eve. Who is nicer than John?', None],
  ['The red car is faster than the blue car. Is the blue car faster than the red car?', False],
  ['The red car is faster than the blue car. Is the green car faster than the red car?', None],

  # -- equality comparisons --

  ['John is as tall as Bill. Is John taller than Bill?', False],
  ["John is as tall as Bill. Is John's height equal to Bill's?", True],

  # -- which-questions on comparatives --

  ['The mountain is higher than the hill. Which is lower, the mountain or the hill?', 'The hill.'],
  ['The mountain is higher than the hill. Is the hill higher than the mountain?', False],
  ["This book is more interesting than that one. Is 'that one' more interesting?", False],

# == COORDINATION (NP, VP, CLAUSAL) ==

  # -- NP coordination with lists --

  ['Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a toy?', True],
  ['Elephants, foxes and rabbits are nice animals and good toys. John is a fox. John is a good toy?', True],
  ['Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal?', True],
  ['Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal and a toy?', True],
  ['Elephants, foxes and rabbits are nice animals and good toys. John is a rabbit. John is an animal or a toy?', True],

  ['Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a bird?', False],
  ['Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is not a bird?', True],
  ['Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a small fish?', False],
  ['Elephants, foxes and rabbits are neither birds nor small fish. John is a rabbit. John is a fish?', None],

  ['Elephants, foxes and rabbits are nice animals and good toys. John is an elephant. John is a red toy?', None],

  # -- either-or coordination --

  ['Elephants and sparrows are either animals or birds. John is a sparrow. John is a bird. John is an animal?', False],
  ['Elephants and sparrows are either animals or birds. John is a sparrow. Sparrows are birds. John is not an animal?', True],
  ['Elephants and sparrows are animals or birds. John is a sparrow. John is a bird. John is an animal or a bird?', True],
  ['Elephants and sparrows are animals or birds. John is a sparrow. John is a bird. John is an elephant?', None],
  ['Elephants or sparrows are animals. John is an elephant. Sparrows are not animals. John is an animal?', True],

  # -- class independence --

  ['Elephants are animals. Birds are animals?', None],
  ['Elephants are animals. Birds are not animals?', None],
  ['Elephants are animals. Birds are nice animals?', None],
  ['Elephants are animals. Birds are not nice animals?', None],

  ['John saw the blue head of the red elephant. John saw the blue head of the red elephant?', True],
  ['John saw the blue head of the red elephant. John saw the red head of the blue elephant?', None],

# == LISTS AND CONJUNCTIONS ==

  # -- conjunction of class properties --

  ['Cars are nice. Cars have brakes. Cars are nice and have brakes?', True],
  ['Cars are nice. Cars are nice and have brakes?', None],
  ['Cars have brakes. Cars are nice and have brakes?', None],
  ['Cars are nice and cool and have brakes. Cars are nice and cool and have brakes?', True],
  ['Cars are nice and cool and have brakes. Cars have brakes and are nice and cool?', True],
  ['Cars are cool and have brakes. Cars are nice and cool and have brakes?', None],
  ['Cars are nice and cool. Cars have brakes and are nice and cool?', None],
  ['Cars have fenders. Cars have brakes. Cars have brakes and fenders?', True],
  ['Cars have fenders. Cars have brakes and fenders?', None],
  ['Cars have brakes. Cars have brakes and fenders?', None],

  # -- NP conjunction as subject --

  ['John and Mary saw the movie. Did Mary see the movie?', True],
  ['John and Mary saw the movie. Did Mary see a play?', None],
  ['John and Mary saw the movie. Who saw the movie?', 'John and Mary.'],

  # -- conjoined adjectives --

  ['A tall and quiet man entered. A man entered?', True],
  ['A tall and quiet man entered. A woman entered?', None],
  ['A tall and quiet man entered. The man was tall?', True],
  ['A tall and quiet man entered. The man was quiet?', True],
  ['A tall and quiet man entered. The man was short?', False],

  ['A red and blue flag waved. The flag was red?', True],
  ['A red and blue flag waved. The flag was blue?', True],

  # -- conjoined objects --

  ['John bought a red car and a blue bicycle. John bought a car?', True],
  ['John bought a red car and a blue bicycle. John bought a bicycle?', True],
  ['John bought a red car and a blue bicycle. Did John buy a truck?', None],
  ['John bought a red car and a blue bicycle. The car was red?', True],
  ['John bought a red car and a blue bicycle. The bicycle was blue?', True],
  ['John bought a red car and a blue bicycle. The car was blue?', False],

  # -- VP conjunction --

  ['The cat sat on the mat and purred. Did the cat purr?', True],
  ['The cat sat on the mat and purred. Did the cat bark?', None],

  # -- conjoined VPs with different objects --

  ['John ate an apple and drank some water. What did John drink?', ['Water.', 'Some water.']],
  ['John ate an apple and drank some water. Did John eat a banana?', None],
  ['The students studied hard and passed the exam. Did the students pass the exam?', True],
  ['The students studied hard and passed the exam. Did the students fail the exam?', False],
  ['The dog barked and the cat ran away. What did the cat do?', 'Ran away.'],

  # -- conjoined verbs, shared object --

  ['Mary washed and dried the cup. Mary washed the cup?', True],
  ['Mary washed and dried the cup. Mary dried the cup?', True],
  ['Mary washed and dried the cup. Did Mary break the cup?', None],

  ['Tom opened the door and the window. Tom opened the door?', True],
  ['Tom opened the door and the window. Tom opened the window?', True],
  ['Tom opened the door and the window. Tom did not open the door?', False],

  ['John bought a red car and a blue bicycle. What did John buy?', 'A red car and a blue bicycle'],
  ['Tom opened the door and the window. What did Tom open?', 'The door and the window'],
  ['Mary washed and dried the cup. Did Mary iron the cup?', None],

  # -- conjunction with can --

  ['John and Eve can swim. Mark and John are animals. Who can swim and is an animal?', 'John'],
  ['John and Eve can swim. Mark and John are animals. Who is an animal and can swim?', 'John'],
  ['John and Eve can swim. Mark is an animal. Who can swim and is an animal?', None],

  # -- either-or --

  ['Either John or Bill went to the store. Did someone go to the store?', True],
  ['Either John or Bill went to the store. Did Mary go to the store?', None],

  # -- class defaults --

  ['Cars are nice. Cars are nice?', True],

  # -- subclass exceptions --

  ['Red cars are not nice. Cars are nice. Cars are nice?', True],
  ['Red cars are not nice. Cars are nice. Red cars are nice?', False],
  ['Red cars are not nice. Cars are nice. Blue cars are nice?', True],

  ['Penguins happily live in water. Penguins happily live in water?', True],
  ['Penguins happily live in cold water. Penguins happily live in cold water?', True],

# == INTERNAL MODIFICATION ==


  # -- basic appositive --

  ['John, a doctor, arrived. John is a doctor?', True],
  ['John, a doctor, arrived. John is a nurse?', None],
  ['Mary, a pilot, smiled. Who is a pilot?', 'Mary.'],
  ['Paul, a carpenter, carried a box. Paul carried a box?', True],
  ['Paul, a carpenter, carried a box. Paul is a plumber?', None],

  ['Anna, the manager, called Eve. Who is the manager?', 'Anna.'],
  ['The manager, Anna, called Eve. Anna is the manager?', True],
  ['The manager, Anna, called Eve. Eve is the manager?', False],

  ['John, my neighbor, owns a bicycle. John owns a bicycle?', True],
  ['My neighbor, John, owns a bicycle. Who is my neighbor?', 'John.'],
  ['Dr. Smith, a surgeon, entered the room. Dr. Smith is a surgeon?', True],
  ['Dr. Smith, a surgeon, entered the room. Dr. Smith is a dentist?', None],

  ['Tom, a friend of Mary, laughed. Tom is a friend of Mary?', True],
  ['Tom, a friend of Mary, laughed. Mary is a friend of Tom?', None],
  ['Tom, a friend of Mary, laughed. Tom is a friend of Eve?', None],

  ['Sara, the sister of Mike, left. Sara is the sister of Mike?', True],
  ['Sara, the sister of Mike, left. Sara is the brother of Mike?', False],

  # -- noun-noun compounds --

  ['A school bus arrived. A bus arrived?', True],
  ['A school bus arrived. A truck arrived?', None],
  ['A chocolate cake fell. A cake fell?', True],
  ['A chocolate cake fell. A pie fell?', None],
  ['A stone wall collapsed. A wall collapsed?', True],
  ['A kitchen door was open. A door was open?', True],

  # -- adjective from noun modifier --

  ['A village road was narrow. A road was narrow?', True],
  ['A coffee cup broke. A cup broke?', True],
  ['A coffee cup broke. A plate broke?', None],
  ['A garden wall was high. A wall was high?', True],
  ['A garden wall was high. A wall was low?', None],

  # -- present participial modifier --

  ['The man carrying a bag waved. The man carried a bag?', True],
  ['The man carrying a bag waved. The man carried a box?', None],

  # -- holding as participial --

  ['The woman holding a lamp sang. The woman held a lamp?', True],
  ['The child wearing a hat ran. The child wore a hat?', True],
  ['The child wearing a hat ran. The child wore a coat?', None],

  # -- containing as participial --

  ['The box containing apples fell. The box contained apples?', True],
  ['The box containing apples fell. The box contained oranges?', None],

  # -- standing as participial --

  ['The man standing by the door coughed. The man stood by the door?', True],
  ['The man standing by the door coughed. The man stood by the window?', None],

  # -- parked as participial --

  ['The car parked behind the house was blue. The car was behind the house?', True],
  ['The car parked behind the house was blue. The car was in front of the house?', False],
  ['The children playing in the garden laughed. The children were in the garden?', True],
  ['The cup filled with water fell. The cup contained water?', True],
  ['The road leading to the village was narrow. The road led to the village?', True],
  ['The road leading to the village was narrow. The road was wide?', False],
  ['The tree growing near the river was tall. The tree grew near the river?', True],

  # -- participial with modified object --

  ['The man carrying a red bag waved. The bag was red?', True],
  ['The man carrying a red bag waved. The bag was blue?', False],
  ['The woman holding a heavy lamp sang. The lamp was heavy?', True],
  ['The woman holding a heavy lamp sang. The lamp was light?', False],
  ['The child wearing a small hat ran. The hat was small?', True],
  ['The letter written by Mary was long. Mary wrote a long letter?', True],
  ['The letter written by Mary was long. The letter was short?', False],
  ['The cake baked by John was sweet. John baked a sweet cake?', True],
  ['The dog chased by the boy was black. The boy chased a black dog?', True],
  ['The dog chased by the boy was black. The dog was white?', False],

  # -- past participial modifier --

  ['The letter written by Mary arrived. Mary wrote the letter?', True],
  ['The cake baked by John was sweet. John baked the cake?', True],
  ['The cake baked by John was sweet. The cake was bitter?', False],
  ['The song sung by Eve was sad. Eve sang the song?', True],

  # -- passive participial --

  ['The dog chased by the boy escaped. The boy chased the dog?', True],
  ['The dog chased by the boy escaped. Did the dog catch the boy?', None],
  ['The woman admired by John smiled. John admired the woman?', True],

  ['The doctor who treated Mary called John. The doctor treated Mary?', True],
  ['The doctor who treated Mary called John. The doctor called John?', True],
  ['The doctor who treated Mary called John. Did the doctor treat John?', None],

  ['The painter who lived in Rome sold a picture. The painter lived in Rome?', True],
  ['The painter who lived in Rome sold a picture. The painter sold a picture?', True],
  ['The painter who lived in Rome sold a picture. Did the painter live in Paris?', None],

  ["John's friend from Paris bought a camera. John had a friend?", True],
  ["John's friend from Paris bought a camera. The friend was from Paris?", True],
  ["John's friend from Paris bought a camera. Was the friend from London?", None],

  ["Mary's brother carrying a box entered. Mary had a brother?", True],
  ["Mary's brother carrying a box entered. The brother carried a box?", True],
  ["Mary's brother carrying a box entered. Did the brother carry a bag?", None],

  ['The student carrying the books greeted the teacher. The student carried the books?', True],
  ['The student carrying the books greeted the teacher. The student greeted the teacher?', True],
  ['The student carrying the books greeted the teacher. Did the student greet the principal?', None],

  ['The letter was written in June. Was the letter written?', True],
  ['Bears ate berries in a forest. Bears did not eat berries in a forest?', False],
  ['Bears ate berries in a forest. Bears did not eat berries in a field?', None],

# == RELATIVE CLAUSES ==

  # -- who-clauses in rules --

  ['Big bears who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', True],
  ['Big bears who have a trunk have a tail. John is a big bear. John has a nose. John has a tail?', None],
  ['Big bears who have a trunk have a tail. John is a bear. John has a trunk. John has a tail?', None],

  ['Big bears who are nice and have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', None],
  ['Big bears who are nice and have a trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', True],
  ['Big bears who are nice and who have a trunk have a tail. John is a big bear. John has a trunk. John has a tail?', None],
  ['Big bears who are nice and who have a trunk have a tail. John is a big bear. John is nice. John has a tail?', None],
  ['Big bears who are nice and who have a trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', True],

  ['Bears who are nice and have a long trunk have a tail. John is a nice big bear. John has a long trunk. John has a tail?', True],
  ['Bears who are nice and have a long trunk have a tail. John is a nice big bear. John has a trunk. John has a tail?', None],
  ['Bears who have a trunk are nice. John is a bear. John has a trunk. John is nice?', True],
  ['Bears who have a trunk are nice. John is a bear. John has a nose. John is nice?', None],

  ['Bears who are nice and eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?', True],
  ['Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats berries. John has a tail?', True],
  ['Bears who are nice and who eat berries have a tail. John is a nice big bear. John eats fish. John has a tail?', None],

  # -- simple who-clauses --

  ['Bears who are big are strong. John is a big nice bear. John is strong?', True],
  ['Bears who are big are strong. John is a bear. John is strong?', None],
  ['Bears who have tails are strong. John is a big nice bear. John has a tail. John is strong?', True],
  ['Bears who have tails are strong. John is a big nice bear.  John is strong?', None],
  ['Bears who eat fish are strong. John eats fish. John is a bear. John is strong?', True],
  ['Bears who eat fish are strong. John is a bear. John is strong?', None],
  ['Bears who eat fish are strong. John eats carrots. John is a bear. John is strong?', None],
  ['Nice bears who have tails are strong. John is a nice bear. John has a tail. John is strong?', True],
  ['Nice bears who have tails are strong. John is a bear. John has a tail. John is strong?', None],
  ['Nice bears who have tails are strong. John is a nice bear. John has a head. John is strong?', None],

  # -- who-clauses with pre-modifier --

  ['Nice bears who are big are strong. John is a big nice bear. John is strong?', True],
  ['Nice bears who are big are strong. John is a nice bear. John is strong?', None],
  ['Nice bears who eat fish are strong. John is a nice bear. John eats fish. John is strong?', True],

  ['Nice bears who eat big fish are strong. John is a nice bear. John eats big fish. John is strong?', True],
  ['Nice bears who eat big fish are strong. John is a nice bear. John eats big carrots. John is strong?', None],
  ['Nice bears who eat big fish are strong. John is a nice bear. John eats fish. John is strong?', None],

  # -- the-definite with who-clause --

  ['The bear who is big is strong. The bear is strong?', True],
  ['The bear who is big is strong. The big bear is strong?', True],
  ['The bear who is big is strong. The big bear is white?', None],
  ['The bear who is big is strong. Who is strong?', ['The big bear', 'The bear who is big.', 'The bear.']],

  ['The bear who is big eats fish. The bear who is big eats fish?', True],
  ['The bear who is white eats fish. The bear who is white eats fish?', True],

  ['The bear who was white ate a fish. The bear who was white ate a fish?', True],
  ['The bear who was white ate a fish. The bear ate a fish?', True],
  ['The bear who was white ate a fish. The white bear ate a fish?', True],

  ['Bears who were nice ate. Nice bears ate?', True],
  ['The bear who was nice ate. The bear ate?', True],

  ['Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat fish?', True],
  ['Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat tables?', None],
  ['Bears who are nice eat fish who are strong. John is a nice bear. Bears who are nice eat fish who are strong?', True],
  ['Bears who are nice eat fish who are strong. John is a nice bear. Nice bears eat strong fish?', True],

  # -- past-tense who-clauses --

  ['The bear who was nice ate the fish who was strong. The bear who was nice ate the fish who was strong?', True],
  ['The bear who was nice ate the fish who was strong. The nice bear ate the strong fish?', True],
  ['The bear who was nice ate the fish who was strong. The bear who was nice ate the fish who was white?', None],

  ['The bear who was nice and white ate the fish who was big. The nice bear ate the big fish?', True],

  # -- conjoined who-clauses --

  ['The bear who was white and ate a fish was cool. The white bear who ate a fish was cool?', True],
  ['The bear who was white and ate a fish was cool. The bear who ate a fish was cool?', True],
  ['The bear who was white and ate a fish was cool. The white bear who ate a fish was strong?', None],
  ['The bear who was white and ate a fish was cool. The black bear who ate a fish was cool?', None],

  ['The bear who was white and ate a big fish was cool. The white bear who ate a big fish was cool? ', True],
  ['The bear who was white and ate a big fish was cool. The white bear who ate a fish was cool? ', True],
  ['The bear who was white and ate a big fish was cool. The white bear who ate a strong fish was cool? ', None],

  ['The nice bear who was white and ate a big fish was cool. The white nice bear who ate a big fish was cool? ', True],
  ['The nice bear who was white and ate a big fish also ate berries. The white nice bear who ate a big fish also ate berries? ', True],
  ['The nice bear who was white and ate a big fish also ate blue berries. The white nice bear who ate a big fish also ate blue berries? ', True],
  ['The nice bear who was white and ate a big fish also ate blue berries. The white nice bear who ate a big fish also ate berries? ', True],
  ['The nice bear who was white and ate a big fish also ate blue berries. The bear ate berries? ', True],
  ['The nice bear who was white and ate a big fish also ate blue berries. The bear ate bread? ', None],

  ['The bear who ate a big fish ate blue berries. The bear who ate a fish also ate blue berries?', True],
  ['The bear who ate a big fish ate blue berries. The bear who ate a fish ate big berries?', None],
  ['The bear who ate a big fish ate blue berries. John is big?', None],
  ['The bear who ate a big fish ate blue berries. John is blue?', None],
  ['The bear who ate a big fish ate blue berries. John is a fish?', None],

  # -- conjoined verbs in who-clause --

  ['The woman who sang and danced smiled. The woman sang?', True],
  ['The woman who sang and danced smiled. The woman danced?', True],
  ['The woman who sang and danced smiled. The woman did not sing?', False],

  ['The boy with a red hat and a blue coat ran. The boy had a red hat?', True],
  ['The boy with a red hat and a blue coat ran. The boy had a blue coat?', True],

  # -- who-clause on object --

  ['Bears eat fish who are strong. John is a bear. John eats strong fish?', True],
  ['Bears eat fish who are strong. John is a fox. John eats strong fish?', None],
  ['Bears eat fish who are strong. John is a bear. John eats red fish?', None],

  ['Bears eat red fish who are strong. John is a bear. John eats red strong fish?', True],
  ['Bears eat red fish who are strong. John is a bear. John eats red fish?', True],
  ['Bears eat red fish who are strong. John is a bear. John eats strong fish?', True],
  ['Bears eat red fish who are strong. John is a bear. John eats yellow strong fish?', None],
  ['Bears eat red fish who are strong. John is a bear. John eats yellow fish?', None],

  # -- subject and object who-clauses --

  ['Bears who are nice eat fish who are strong. John is a nice bear. John eats strong fish?', True],
  ['Bears who are nice eat fish who are strong. John is a bear. John eats strong fish?', None],
  ['Bears who are nice eat fish who are strong. John is a nice bear. John eats yellow fish?', None],

  ['Bears who are nice and white eat fish who are strong and red. John is a nice white bear. John eats red strong fish?', True],
  ['Bears who are nice and white eat fish who are strong and red. John is a nice bear. John eats red strong fish?', None],
  ['Bears who are nice and white eat fish who are strong and red. John is a nice white bear. John eats yellow strong fish?', None],

  # -- which-clauses on objects --

  ['A man liked a car which a woman bought. The car was red. The man liked the car which a woman bought?', True],
  ['A man liked a car which a woman bought. The car was red. The man liked the red car which a woman bought?', True],
  ['A man liked a car which a woman bought. The car was red. The man liked a car which a boy bought?', None],
  ['A man liked a car which a woman bought. The car was red. A man liked a red car which a woman bought?', True],
  ['A man liked a car which a woman bought. The car was red. The man did not like the red car which the woman bought?', False],
  ['A man liked a car which a woman bought. The car was red. The man did not like the red car which a woman bought?', False],

  # -- which-clause with pronoun --

  ['A man liked a car which he bought. The car was red. The man bought the red car?', True],
  ['A man liked a car which he bought. The car was red. A man bought a red car?', True],

  # -- which-clause adding properties --

  ['John has a red car which is nice and big. The nice car is big and red?', True],
  ['John has a red car which is nice and big. The car is good?', None],
  ['John lives in a nice car which was red and was bought by Mike. John lives in a car which was bought by Mike?', True],
  ['Bears ate berries in a forest which was bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  ['Bears ate berries in a forest which was seen by Mary. Bears ate berries in the forest seen by Mary?', True],
  ['Bears ate berries in a forest which was bought by Mike. Bears ate berries in the forest bought by Mike?', True],
  ['Bears ate berries in a forest which was bought by Mary. Bears ate berries in the forest bought by John?', None],
  ['John lives in a red car bought by Mary. Mary bought the car?', True],

  ['Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest which was bought by Mary?', True],
  ['Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest which was bought by John?', None],
  ['Mike ate berries in the forest which was bought by Mary. Mike ate berries in the forest bought by Mary?', True],

  ['Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by Mary?', True],
  ['Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest which was bought by John?', None],
  ['Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by Mary?', True],
  ['Bears ate berries in the forest which was bought by Mary. Bears ate berries in the forest bought by John?', None],

  ['A man had a car which a woman bought. The car was red. Who had a red car?', ['The man', 'The man and the woman.', 'The woman.']],

  # -- which-clause on location --

  ['Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest which was bought by her?', True],
  ['Bears ate nice berries in a big forest which was seen by Mary. Bears ate berries in the forest which was seen by her?', True],
  ['Bears ate nice berries in a big forest which was bought by Mike. Bears ate berries in the forest which was bought by him?', True],
  ['Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest which was bought by a man?', None],
  ['Bears ate nice berries in a big forest which was bought by Mary. Bears ate berries in the forest?', True],

  ['Bears ate berries in the forest which was bought by Mary. The forest was bought by Mary?', True],

  # -- which-clause on location object --

  ['John lives in a car which is red. The car is red?', True],
  ['John lives in a car which is red. The car is nice?', None],
  ['John lives in a car which is red. John lives in a red car?', True],
  ['John lives in a car which is red. John lives in a nice car?', None],

  ['John lives in a car which is red and was bought by Mary. The nice car was bought by Mary?', None],

  ['John has a car which is nice and red. The car is red and nice?', True],
  ['John has a car which is nice and red. The red car is nice?', True],
  ['John has a car which is nice and red. The big car is nice?', None],

  # -- named entities in which-clauses --

  ['John had a car which Eve bought. John had a car which Eve bought?', True],
  ['John had a car which Eve bought. John had a car which Eve saw?', None],
  ['John had a car which Eve bought. John had a car which Mike bought?', None],
  ['John had a car which Mike bought. John had a car Mike bought?', True],
  ['John had a car which Eve bought. John had a car Eve saw?', None],
  ['John had a car which Eve bought. John had a car Mike bought?', None],
  ['John had a car Mike bought. John had a car Mike bought?', True],
  ['John had a car Eve bought. John had a car Mike bought?', None],
  ['John had a car Eve bought. John had a car Eve saw?', None],
  ['John had a car Eve bought. John had a car which Eve bought?', True],
  ['John had a car Eve bought. John had a car which Eve saw?', None],
  ['John had a car Eve bought. John had a car which Mike bought?', None],
  ['John had a car Eve bought. Eve bought a car?', True],

  ['John had a car Eve liked. Eve had a car?', None],

  ['John had a red car Eve bought. John had a car which Eve bought?', True],
  ['John had a red car which Mike bought. John had a car Mike bought?', True],
  ['John had a red car Eve bought. John had a black car which Eve bought?', None],
  ['John had a red car which Eve bought. John had a black car Eve bought?', None],

  ['John had a car Eve bought. John had a car which Eve did not buy?', None],
  ['John had a car which Mike did not buy. John had a car Mike did not buy?', True],
  ['John did not have a red car which Eve bought. John did not have a red car which Eve bought?', True],

  # -- drove + which-clause --

  ['John drove a car which Eve bought. John drove a car which Eve bought?', True],
  ['John drove a car which Eve bought. John drove a car which Eve saw?', None],
  ['John drove a car which Eve bought. John drove a car which Mike bought?', None],
  ['John drove a car which Eve bought. John drove a car Eve bought?', True],
  ['John drove a car which Eve bought. John drove a car Eve saw?', None],
  ['John drove a car which Eve bought. John drove a car Mike bought?', None],
  ['John drove a car Mike bought. John drove a car Mike bought?', True],
  ['John drove a car Eve bought. John drove a car Mike bought?', None],
  ['John drove a car Eve bought. John drove a car Eve saw?', None],
  ['John drove a car Mike bought. John drove a car which Mike bought?', True],
  ['John drove a car Eve bought. John drove a car which Eve saw?', None],
  ['John drove a car Eve bought. John drove a car which Mike bought?', None],
  ['John drove a car Eve bought. Eve drove a car?', None],
  ['John drove a car Eve bought. John drove a car?', True],

  ['John drove a red car Mike bought. John drove a car which Mike bought?', True],
  ['John drove a red car which Eve bought. John drove a car Eve bought?', True],
  ['John drove a red car Eve bought. John drove a black car which Eve bought?', None],
  ['John drove a red car which Eve bought. John drove a black car Eve bought?', None],

  ['John drove a car Eve bought. John drove a car which Eve did not buy?', None],
  ['John drove a car which Mike did not buy. John drove a car Mike did not buy?', True],

  # -- whom-clauses --

  ['John is a man whom Eve liked. John is a man whom Eve liked?', True],
  ['John is a man whom Eve liked. John is a man whom Eve saw?', None],
  ['John is a man whom Eve liked. John is a man whom Mike liked?', None],
  ['John is a man whom Eve liked. John is a man Eve liked?', True],
  ['John is a man whom Eve liked. John is a man Eve saw?', None],
  ['John is a man whom Eve liked. John is a man Mike liked?', None],

  # -- reduced whom-clauses --

  ['John is a man Eve liked. John is a man Eve liked?', True],
  ['John is a man Eve liked. John is a man Mike liked?', None],
  ['John is a man Eve liked. John is a man Eve saw?', None],
  ['John is a man Eve liked. John is a man whom Eve liked?', True],
  ['John is a man Eve liked. John is a man whom Eve saw?', None],
  ['John is a man Eve liked. John is a man whom Mike liked?', None],

  ['John is a strong man Eve liked. John is a strong man whom Eve liked?', True],
  ['John is a strong man whom Eve liked. John is a strong man Eve liked?', True],
  ['John is a strong man Eve liked. John saw a strong man whom Eve liked?', None],
  ['John is a strong man whom Eve liked. John saw a strong man Eve liked?', None],

  ['John is a man Eve liked. John is a man whom Eve did not like?', False],
  ['John is a man whom Eve did not like. John is a man Eve did not like?', True],

  ['John is not a man whom Eve liked. John is not a man whom Eve liked?', True],
  ['John is a man Eve liked. John is a man?', True],
  ['John is a man Eve liked. Eve liked John?', True],
  ['John is a man Mary liked. Mary liked a man?', True],
  ['John is a man Mary liked. Mary liked the man?', True],

  # -- that-clauses --

  ['The book that Mary bought is on the table. Who bought the book?', 'Mary.'],
  ['The book that Mary bought is on the table. Did John buy the book?', None],
  ['The car which John drove was red. What color was the car?', 'Red.'],
  ['The car which John drove was red. Was the car blue?', False],
  ['The student who passed the test studied a lot. Did the student study?', True],
  ['The student who passed the test studied a lot. Did the student fail the test?', False],

  ['The man who laughed and who waved left. The man laughed?', True],
  ['The man who laughed and who waved left. The man waved?', True],
  ['The man who laughed and who waved left. Did the man cry?', None],

  # -- who-clause queries --

  ['The man who saw John is tall. Who saw John?', 'The man.'],
  ['The man who saw John is tall. Did John see the man?', None],
  ['The man whom John saw is tall. Who did John see?', ['The man.', 'The tall man.']],
  ['The man whom John saw is tall. Is the man short?', False],

  # -- have with relative clauses --

  ['A man had a car which a nice woman bought. The car was red. Who bought the red car?', 'The nice woman'],
  ['A man had a car which a nice woman bought. The car was red. Who bought a car?', 'The nice woman'],
  ['A man had a car which a nice woman bought. The car was red. Who was nice?', 'The woman'],
  ['A man had a car which a nice woman bought. The car was red. Who was nice and bought a car?', ['The woman', 'The nice woman.']],
  ['A man had a car which a nice woman bought. The car was red. Who bought the black car?', None],

  ['A big bear was strong. The bear was nice. Who was nice and strong?', ['The big bear.', 'The bear.']],

  ['A big bear was strong. The small bear was nice. Who was nice and strong?', None],
  ['A big bear was strong. The small bear was nice. Who was nice?', 'The small bear.'],
  ['A big bear was strong. The small bear was nice. Who was strong?', 'The big bear.'],

  ['A bear was strong. The bear was nice. Who was nice and strong?', 'The bear.'],
  ['The big bear is strong. Who is strong?', 'The big bear'],
  ['A man liked a car. The man did not like the car?', False],

  ['A man liked a car which a woman bought. The car was red. A man liked a car?', True],
  ['A man liked a car which a woman bought. The car was red. The man liked the car?', True],
  ['A man liked a car which a woman bought. The car was red. The man liked a red car?', True],
  ['A man liked a car which a woman bought. The car was red. The man liked the bike?', None],
  ['A man liked a car which a woman bought. The car was red. The man liked a black car?', None],
  ['A man liked a car which a woman bought. The car was red. The man liked the red car?', True],

  # -- indefinite subject with which-clause --

  ['A man had a car which a woman bought. A man had a car which a woman bought?', True],
  ['A man had a car a woman bought. A man had a car which a woman bought?', True],
  ['A man had a car which a woman bought. A man had a car which a woman liked?', None],
  ['A man had a car which a woman bought. A man had a car which a man bought?', None],
  ['A man had a car a woman bought. A woman bought a car?', True],
  ['A man had a car a woman bought. The woman bought a car?', True],
  ['A man had a car a woman bought. The woman did not buy a car?', False],
  ['A man had a car a woman bought. A man had a bike?', None],
  ['A man had a car a woman bought. A woman bought a red car?', None],
  ['A man had a car a woman bought. A man bought a car?', None],
  ['A man had a car a woman bought. The man did not have a car?', False],

  # -- indefinite drove + which --

  ['A man drove a car which a woman bought. A man drove a car which a woman bought?', True],
  ['A man drove a car a woman bought. A man drove a car which a woman bought?', True],
  ['A man drove a car which a woman bought. A man drove a car a woman bought?', True],
  ['A man drove a car which a woman bought. A man drove a car which a woman liked?', None],
  ['A man drove a car which a woman bought. A man drove a car?', True],
  ['A man drove a car which a woman bought. A man drove the car?', True],
  ['A man drove a car which a woman bought. A woman drove the car?', None],
  ['A man drove a car which a woman bought. A woman bought a car?', True],
  ['A man drove a car which a woman bought. A woman bought the car?', True],

  ['A man had a car which a woman bought. A man had a car?', True],
  ['A man had a car which a woman bought. A man had the car?', True],
  ['A man had a car which a woman bought. A woman bought a car?', True],
  ['A man had a car which a woman bought. A woman bought the car?', True],

  # -- which-clause with follow-up facts --

  ['A man had a car which a woman bought. The car was red. A man had a car?', True],
  ['A man had a car which a woman bought. The car was red. The man had the car?', True],
  ['A man had a car which a woman bought. The car was red. The man had a red car?', True],
  ['A man had a car which a woman bought. The car was red. The man had the bike?', None],
  ['A man had a car which a woman bought. The car was red. The man had a black car?', None],
  ['A man had a car which a woman bought. The car was red. The man had the red car?', True],
  ['A man had a car which a woman bought. The car was red. The man had the car which a woman bought?', True],
  ['A man had a car which a woman bought. The car was red. The man had the red car which a woman bought?', True],
  ['A man had a car which a woman bought. The car was red. The man had a car which a boy bought?', None],
  ['A man had a car which a woman bought. The car was red. A man had a red car which a woman bought?', True],
  ['A man had a car which a woman bought. The car was red. The man did not have the red car which a woman bought?', False],

  ['A man had a car which he bought. The car was red. The man bought the red car?', True],
  ['A man had a car which he bought. The car was red. A man bought a red car?', True],

  # -- nested who/which clauses --

  ['Bears who eat fish which are big are strong. John is a bear. John eats fish. John is strong?', None],
  ['Bears who eat fish which are big are strong. John is a bear. John eats big apples. John is strong?', None],

  # -- nested who+which clauses --

  ["""A man who ate breakfast liked a car which a woman bought. The car was red.
     A man who ate breakfast liked a red car which a woman bought?""", True],
  ["""A man who ate breakfast liked a car.
     The man ate breakfast?""", True],
  ["""A man who ate breakfast liked a car which a woman bought. The car was red.
     The man who ate breakfast liked the red car which the woman bought?""", True],
  ["""A man who ate breakfast liked a car which a woman bought. The car was red.
     The man who ate breakfast liked the red car which a woman bought?""", True],

  ['A man liked a car which a woman bought. The car was red. Who liked a red car?', 'The man'],

  ['A man liked a car which a nice woman bought. The car was red. Who bought the red car?', 'The nice woman'],
  ['A man liked a car which a nice woman bought. The car was red. Who bought a car?', 'The nice woman'],
  ['A man liked a car which a nice woman bought. The car was red. Who was nice?', 'The woman'],
  ['A man liked a car which a nice woman bought. The car was red. Who was nice and bought a car?', 'The woman'],
  ['A man liked a car which a nice woman bought. The car was red. Who bought the black car?', None],

  # -- complex: who + which + follow-up --

  ["""A man who ate breakfast had a car which a woman bought. The car was red.
     A man who ate breakfast had a red car which a woman bought?""", True],
  ["""A man who ate breakfast had a car.
     The man ate breakfast?""", True],
  ["""A man who ate breakfast had a car which a woman bought. The car was red.
     The man who ate breakfast had the red car which the woman bought?""", True],
  ["""A man who ate breakfast had a car which a woman bought. The car was red.
     The man who ate breakfast had the red car which a woman bought?""", True],

# == AMBIGUOUS MODIFIER SCOPE ==

  # -- manner adverb --

  ['John ate the apple quickly. How did John eat the apple?', 'Quickly.'],
  ['John ate the apple quickly. Did John eat a banana?', None],
  ['Mary visited London in September. When did Mary visit London?', 'In September.'],
  ['Mary visited London in September. Did Mary visit Paris?', None],

  # -- adjectival modifier --

  ['The blue bird sang a beautiful song. What color was the bird?', 'Blue.'],
  ['The blue bird sang a beautiful song. Was the bird red?', False],
  ['The tall man walked into the small room. Who walked into the room?', ['The tall man.', 'The man.']],
  ['John works at the hospital every day. Where does John work?', 'At the hospital.'],
  ['John works at the hospital every day. Does John work at the school?', None],
  ['The old wooden bridge collapsed yesterday. What happened to the bridge?', 'It collapsed.'],

  # -- instrument PP --

  ['John ate berries with the help of a spoon. John ate berries with the help of a spoon?', True],
  ['John ate berries with the help of a spoon. John ate berries with the help of a spade?', None],

  # -- with-PP ambiguity --

  ['John saw the man with a telescope. John saw the man?', True],
  ['John saw the man with a telescope. The man had a telescope?', None],

  # -- in-PP ambiguity --

  ['John saw the bird in the garden. John saw the bird?', True],
  ['John saw the bird in the garden. The bird was in the garden?', True],
  ['John saw the bird in the garden. Did John see a fish in the garden?', None],

  # -- on-PP ambiguity --

  ['John ate the pizza on the table. Where was the pizza?', 'On the table.'],
  ['John ate the pizza on the table. Was the pizza on the floor?', False],
  ['John ate the pizza on the table. Did John eat a sandwich?', None],

  ['The cat in the hat sat on the mat. Where was the cat?', ['In the hat.', 'On the mat.']],
  ['Mary put the book on the shelf in the library. Where is the shelf?', 'In the library.'],
  ['Mary put the book on the shelf in the library. Did Mary put a magazine on the shelf?', None],

  # -- under-PP --

  ['Mary found the key under the table. Mary found the key?', True],
  ['Mary found the key under the table. The key was under the table?', True],
  ['Mary found the key under the table. Was the key on the table?', False],

  ['Tom put the book on the chair. The book was on the chair?', True],
  ['Eve kept the milk in the fridge. The milk was in the fridge?', True],

  # -- from-PP --

  ['John met the girl from Paris. John met the girl?', True],
  ['John met the girl from Paris. The girl was from Paris?', True],
  ['Mary called the boy in the kitchen. Mary called the boy?', True],
  ['Mary called the boy in the kitchen. The boy was in the kitchen?', True],

  # -- classic PP-attachment ambiguity --

  ['John shot an elephant in his pyjamas. The elephant was in his pyjamas?', None],
  ['John shot an elephant in his pyjamas. John shot in his pyjamas?', True],

  ['John ate berries in a forest with a spoon. John ate berries in a forest with a spoon?', True],
  ['John ate berries in a forest with a spoon. John ate berries in a field?', None],
  ['John ate berries in a forest with a spoon. John ate berries in a nice forest with a spoon?', None],
  ['John ate berries in a forest with a spoon. John ate berries in a nice forest?', None],
  ['John ate berries in a forest with a spoon. John ate berries with a spoon in a nice forest?', None],

# == PASSIVE VOICE ==

  # -- basic passive --

  ['John is defeated. Mike is defeated?', None],
  ['John is defeated. John is defeated?', True],
  ['John is defeated. Who is defeated?', 'John'],
  ['John is defeated. John is not defeated?', False],
  ['John and Mike were defeated. Who defeated John?', None],
  ['John and Mike were defeated. Who defeated John and Mike?', None],

  ['An apple was eaten. John ate a pear. What was eaten?', ['The apple and the pear.', 'An apple and a pear.', 'An apple.', 'A pear.']],
  ['John was nice and defeated. John was nice and defeated?', True],
  ['John was nice and defeated. John was nice?', True],
  ['John was defeated. John was defeated?', True],
  ['John was defeated. John is defeated?', None],

  # -- active/passive equivalence --

  ['Clinton defeated Dole. Clinton defeated Dole?', True],
  ['Clinton defeated Dole. Clinton defeated Mike?', None],
  ['Dole was defeated by Clinton. Dole was defeated by Clinton?', True],
  ['Dole was defeated by Clinton. Dole was defeated by Mike?', None],
  ['Clinton defeated Dole. Dole was defeated by Clinton?', True],
  ['Clinton defeated Dole. Dole was defeated by Mike?', None],
  ['Dole was defeated by Clinton. Clinton defeated Dole?', True],
  ['Dole was defeated by Clinton. Mike defeated Dole?', None],

  # -- passive with by-phrase --

  ['The window was broken by John. John broke the window?', True],
  ['The window was broken by John. Did Mary break the window?', None],
  ['The song was sung by Mary. Mary sang the song?', True],
  ['The letter was written by Eve. Eve wrote the letter?', True],
  ['The letter was written by Eve. Did Tom write the letter?', None],
  ['The house was built by Tom. Tom built the house?', True],
  ['The house was built by Tom. Tom destroyed the house?', None],
  ['The bicycle was repaired by Anna. Anna repaired the bicycle?', True],
  ['The bicycle was repaired by Anna. Anna broke the bicycle?', None],
  ['The cake was eaten by the child. The child ate the cake?', True],
  ['The ball was kicked by Mike. Mike kicked the ball?', True],
  ['The ball was kicked by Mike. Did Mike catch the ball?', None],
  ['The tree was cut by the farmer. The farmer cut the tree?', True],
  ['The book was read by Sara. Sara read the book?', True],
  ['The book was read by Sara. Did Sara write the book?', None],
  ['The car was washed by Paul. Paul washed the car?', True],
  ['The room was cleaned by the maid. The maid cleaned the room?', True],
  ['The picture was painted by Leo. Leo painted the picture?', True],

  # -- agentless passive --

  ['The window was broken. John broke the window?', None],
  ['The letter was written. Mary wrote the letter?', None],
  ['The cake was eaten. Who ate the cake?', None],
  ['The room was cleaned. Who cleaned the room?', None],
  ['The glass was broken by the boy. Who broke the glass?', 'The boy.'],

  # -- passive ditransitive --

  ['Mary was given a promotion. Who received a promotion?', 'Mary.'],
  ['A promotion was given to Mary. What did Mary get?', 'A promotion.'],
  ['The city was destroyed. Is the city destroyed?', True],
  ['The city was destroyed. Is the city intact?', False],
  ['The mouse was chased by the cat. Who was the cat chasing?', 'The mouse.'],
  ['The mouse was chased by the cat. Did the mouse chase the cat?', False],
  ['The bill was paid by John. Did John pay the bill?', True],
  ['The bill was paid by John. Did Mary pay the bill?', None],

# == SUBORDINATE CLAUSES ==

  # -- reported speech --

  ['John said that Mary left. Mary left?', True],
  ['John said that Mary left. Did Mary stay?', None],
  ['Eve reported that Tom arrived. Tom arrived?', True],
  ['Eve reported that Tom arrived. Did Tom depart?', None],
  ['Anna announced that the show started. The show started?', True],
  ['The guide explained that the road was closed. The road was closed?', True],
  ['The guide explained that the road was closed. Was the road open?', False],

  # -- infinitival purpose clause --

  ['John went to the shop to buy bread. John went to the shop?', True],
  ['John went to the shop to buy bread. John bought bread?', None],
  ['John went to the shop to buy bread. Did John go to the bank?', None],

  ['Mary opened the window to let in air. Mary opened the window?', True],
  ['Mary opened the window to let in air. Mary did not open the window?', False],
  ['Mary opened the window to let in air. Air came in?', None],

  # -- concessive: although --

  ['Although John was tired, he finished the work. John was tired?', True],
  ['Although John was tired, he finished the work. John finished the work?', True],
  ['Although John was tired, he finished the work. John did not finish the work?', False],
  ['Although John was tired, he finished the work. Was the work difficult?', None],

  # -- concessive: though --

  ['Though Mary was ill, she traveled. Mary was ill?', True],
  ['Though Mary was ill, she traveled. Mary traveled?', True],
  ['Though Mary was ill, she traveled. Mary did not travel?', False],
  ['Though Mary was ill, she traveled. Did Mary recover?', None],

  # -- sentence adverbials --

  ['Fortunately, John found the key. John found the key?', True],
  ['Fortunately, John found the key. John did not find the key?', False],
  ['Fortunately, John found the key. Did John find the lock?', None],

  ['Sadly, Mary lost the letter. Mary lost the letter?', True],
  ['Unexpectedly, the door opened. The door opened?', True],
  ['Unexpectedly, the door opened. The door did not open?', False],
  ['Apparently, Tom left early. Tom left early?', True],

  ['Mary said that she was tired. Who was tired?', 'Mary.'],
  ['Mary said that she was tired. Was Mary happy?', None],
  ['A surgeon, Dr. Smith, entered the room. Who entered the room?', ['Dr. Smith.', 'A surgeon.']],
  ['The horse kept in the stable was calm. The horse was in the stable?', True],

# == ELLIPSIS & GAPPING ==

  # -- gapping --

  ['John likes tea and Mary coffee. What does Mary like?', 'Coffee.'],
  ['John likes tea and Mary coffee. Does Mary like tea?', None],

  # -- locative gapping --

  ['John went to Paris and Mary to London. Where did Mary go?', ['London.', 'To London.']],
  ['John went to Paris and Mary to London. Did Mary go to Paris?', False],
  ['Paul ate a sandwich and Bill a salad. What did Bill eat?', 'A salad.'],
  ['Paul ate a sandwich and Bill a salad. Did Paul eat a salad?', None],

  # -- VP ellipsis with did-too --

  ['John saw the doctor and Mary did too. Did Mary see the doctor?', True],
  ['John saw the doctor and Mary did too. Did Mary see the dentist?', None],
  ['John bought a book, and Bill said Peter did too. Did Bill say Peter bought a book?', True],

  # -- conditional did-too --

  ['If John wrote a report, then Bill did too. John wrote a report. Did Bill write a report?', True],
  ['If John wrote a report, then Bill did too. John wrote a report. Did Bill write a novel?', None],

# == ACTION MODES & HABITS ==

  # -- action with location --

  ['Bears eat berries in a forest. Bears eat berries in a forest?', True],
  ['Bears eat berries in a forest. Bears eat berries in a big forest?', None],
  ['Bears do not eat berries in a forest. Bears eat berries in a forest?', False],

  # -- action with manner adverb --

  ['Bears quickly eat berries in a forest. Bears eat berries?', True],
  ['Bears quickly eat berries in a forest. Bears quickly eat berries?', True],
  ['Bears quickly eat berries in a forest. Bears slowly eat berries?', None],

  ['Bears eat red berries in a forest. Bears eat berries in forest?', True],
  ['Bears do not eat red berries in a forest. Bears eat red berries in forest?', False],

  ['Bears eat berries in a deep forest. Bears eat berries?', True],
  ['Bears eat berries in a deep forest. Bears eat berries in a deep forest?', True],
  ['Bears eat berries in a deep forest. Bears eat berries in a forest?', True],
  ['Bears eat berries in a deep forest. Bears eat berries in a shallow forest?', None],

  # -- action with modified arguments --

  ['Bears eat red berries in a deep forest. John is a bear. John eats red berries in a deep forest?', True],
  ['Bears eat red berries in a deep forest. John is a bear. John eats no berries?', False],
  ['Bears eat berries in a deep forest. John is a bear. John eats berries in a shallow forest?', None],
  ['Bears quickly eat berries in a deep forest. John is a bear. John quickly eats berries in a deep forest?', True],

  ["""If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John quickly eats berries in a deep forest. John is hungry?""", True],
  ["""If a bear quickly eats berries in a deep forest, it is hungry. John is a bear.
     John eats berries in a deep forest. John is hungry?""", None],
  ["""If a bear quickly eats berries in a deep forest, it is hungry. John is a fox.
     John quickly eats berries in a deep forest. John is hungry?""", None],

  ["""If a bear eats berries in a forest, it is hungry. John is a brown bear.
      John quickly eats berries in a deep forest. Who is hungry?""", 'John.'],
  ["""If a bear eats berries in a forest, it is hungry. John is a brown bear.
      John draws berries in a deep forest. Who is hungry?""", None],
  ["""If a bear eats, it is hungry. John is a brown bear.
      John quickly eats berries in a deep forest. Who is hungry?""", 'John.'],

  # -- habitual location --

  ['Penguins live in the water. Penguins live in the water?', True],
  ['Penguins live in the water. Penguins live in water?', True],
  ['Penguins live in the water. Penguins live in stone?', None],
  ['Penguins live in the water. Penguins live in the stone?', None],
  ['Penguins live in water. Penguins live in water?', True],
  ['Penguins live in water. Penguins live in stone?', None],
  ['Penguins live in water. Penguins live in the stone?', None],

  ['Penguins happily live in cold water. Penguins live in water?', True],
  ['Penguins happily live in cold water. Penguins live in cold water?', True],
  ['Penguins happily live in cold water. Penguins live in hot water?', None],

  ['Bears eat berries in a forest. Bears eat berries in forest?', True],
  ['Bears eat berries in a forest. Bears do not eat berries in forest?', False],
  ['Bears eat berries in a forest. Bears eat berries in a field?', None],
  ['Bears eat berries in a forest. Bears eat berries?', True],

# == TRANSFER OF POSSESSION (GIVE/TAKE) ==

  # -- basic give/receive --

  ['John gave Mary a book. Who received a book?', 'Mary.'],
  ['John gave Mary a book. Did John receive a book?', None],
  ['John gave a book to Mary. What did Mary receive?', ['A book.', 'The book.']],
  ['John gave a book to Mary. Did Eve receive a book?', None],

  # -- hand: transfer variant --

  ['Anna handed Mark a key. Mark got a key?', True],
  ['Anna handed a key to Mark. Anna handed Mark a key?', True],
  ['Anna handed a key to Mark. Did Anna hand Mark a lock?', None],

  # -- show/see inference --

  ['The teacher showed the students the map. Who saw the map?', ['The students.', 'The teacher and the students.']],
  ['The teacher showed the students the map. Did the teacher show a book?', None],
  ['The teacher showed the map to the students. What did the teacher show?', 'The map.'],

  # -- tell: communication transfer --

  ['John told Mary a story. Mary heard a story?', True],
  ['John told Mary a story. Did Mary tell John a story?', None],
  ['John told a story to Mary. Who heard a story?', 'Mary.'],

  ['The guide offered the tourists tea. Did the guide offer coffee?', None],

  # -- for-benefactive --

  ['The chef cooked a meal for the guests. Who was the meal for?', 'The guests.'],
  ['The chef cooked a meal for the guests. Did the chef eat the meal?', None],

  # -- reflexive transfer --

  ['Susan bought herself a new car. Who owns a new car?', 'Susan.'],
  ['Susan bought herself a new car. Did Tom buy a car?', None],
  ['Susan bought a new car for herself. What did Susan buy?', ['A new car.', 'A car.']],

  ['John gave Mary a book. Mary got a book?', True],
  ['John gave Mary a book. Did Mary give John a book?', None],
  ['John gave a book to Mary. Mary got a book?', True],

  ['Eve sent Tom a letter. Did Tom send Eve a letter?', None],
  ['Eve sent a letter to Tom. Who got a letter?', 'Tom.'],
  ['The teacher showed the students a map. The students saw a map?', True],
  ['The teacher showed the students a map. Did the students see a globe?', None],
  ['The teacher showed a map to the students. Who saw a map?', ['The students.', 'The teacher and the students.']],

  # -- give with modified object --

  ['John gave Mary a red book. Mary got a red book?', True],
  ['John gave Mary a red book. Mary got a blue book?', None],
  ['Eve sent Tom a long letter. Tom got a short letter?', None],
  ['Anna handed Mark a silver key. Mark got a silver key?', True],
  ['The teacher showed the students a large map. The students saw a large map?', True],
  ['The teacher showed the students a large map. Did the students see a small map?', None],

  ['Bears eat red berries in a forest. Bears eat red berries in forest?', True],
  ['Bears eat red berries in a forest. Bears eat yellow berries in forest?', None],

# == TENSE, ASPECT & CHANGE OF STATE ==

  # -- did-emphasis --

  ['A man did have a car. A man had a car?', True],
  ['A man had a car. A man did have a car?', True],
  ['The man has a car. The man does have a car?', True],
  ['A man had a car. A man has a car?', True],
  ['A man had a car. The man has a car?', True],

  # -- perfective aspect --

  ['John has finished his homework. Is the homework finished?', True],
  ['John has finished his homework. Is the homework unfinished?', False],
  ['John has finished his homework. Has John finished his project?', None],

  # -- progressive aspect --

  ['Mary was reading a book when the phone rang. What was Mary doing?', 'Reading a book.'],
  ['Mary was reading a book when the phone rang. Did the doorbell ring?', None],

  # -- future tense --

  ['John will go to the store tomorrow. Has John already gone to the store?', False],

  # -- present for scheduled events --

  ['The train leaves at noon. When does the train leave?', 'At noon.'],
  ['The train leaves at noon. Does the train leave at midnight?', False],

  # -- temporal subordinate: before --

  ['Before John left, he locked the door. John locked the door?', True],
  ['Before John left, he locked the door. John left?', True],
  ['Before John left, he locked the door. Did John lock the window?', None],

  # -- temporal subordinate: after --

  ['After Mary arrived, she called Tom. Mary arrived?', True],
  ['After Mary arrived, she called Tom. Mary called Tom?', True],
  ['After Mary arrived, she called Tom. Did Mary call Eve?', None],

  # -- temporal subordinate: when --

  ['When Eve entered the house, she smiled. Eve entered the house?', True],
  ['When Eve entered the house, she smiled. Eve did not enter the house?', False],
  ['When Eve entered the house, she smiled. Eve smiled?', True],

  # -- temporal subordinate: while --

  ['While John was cooking, Mary read a book. John cooked?', True],
  ['While John was cooking, Mary read a book. Did John read a book?', None],
  ['While John was cooking, Mary read a book. Mary read a book?', True],

  ['As Tom walked home, it rained. Tom walked home?', True],
  ['As Tom walked home, it rained. It rained?', True],
  ['As Tom walked home, it rained. Did it snow?', None],

  # -- temporal subordinate: once --

  ['Once Anna found the key, she opened the box. Anna found the key?', True],
  ['Once Anna found the key, she opened the box. Anna opened the box?', True],
  ['Once Anna found the key, she opened the box. Did Anna close the box?', None],

  # -- temporal subordinate: since --

  ['Since Mike lost his ticket, he stayed outside. Mike lost his ticket?', True],
  ['Since Mike lost his ticket, he stayed outside. Mike stayed outside?', True],
  ['Since Mike lost his ticket, he stayed outside. Did Mike find his ticket?', None],

  ['Until Sara arrived, John waited. Sara arrived?', True],
  ['Until Sara arrived, John waited. John waited?', True],

  ['After John bought a car, he washed it. John bought a car?', True],
  ['After John bought a car, he washed it. John washed the car?', True],
  ['After John bought a car, he washed it. Did John sell the car?', None],

  ['Before Mary wrote a letter, she found a pen. Mary found a pen?', True],
  ['Before Mary wrote a letter, she found a pen. Did Mary find a pencil?', None],

  # -- change-of-state verbs --

  ['John stopped smoking. Did John smoke in the past?', True],
  ['John stopped smoking. Does John smoke now?', False],
  ['Mary started the car. Was the car running before?', False],
  ['The rain continued. Was it raining earlier?', True],

# == SPATIAL LOGIC & WHERE QUERIES ==

  # -- basic location assertions --

  ['We are in the barn. We are in the barn?', True],
  ['We are in the barn. We are in the shop?', None],
  ['We are in the barn. We are on the barn?', None],

  ['Agatha is in trouble. Agatha is in trouble?', True],
  ['Agatha is in trouble. Agatha is in the barn?', None],
  ['Agatha is in trouble. Agatha is through trouble?', None],

  # -- existential location --

  ['There is a ghost in the room. There is a ghost in the room?', True],
  ['There is a ghost in the room. A ghost is in the room?', True],
  ['There is a ghost in the room. There is a lamp in the room?', None],
  ['There is a ghost in the room. There is a ghost in the barn?', None],

  ['These links present the many viewpoints that existed. These links present the lemmas that existed?', None],

  # -- basic where-questions --

  ['John is in a box. Mark is in a house. Where is John?', ['In the box.', 'In a box.']],
  ['John is in a box. Mark is in a house. Where is Mark?', 'In the house.'],
  ['John is on a box. Mark is on a house. Where is John?', ['On the box.', 'On a box.']],
  ['John is on a box. Mark is on a house. Where is Mark?', ['On the house.', 'On a house.']],
  ['John is at a box. Mark is at a house. Where is John?', ['At the box.', 'At a box.']],
  ['John is at a box. Mark is at a house. Where is Mark?', ['At the house.', 'At a house.']],

  ['John is near a box. Mark is near a house. Where is John?', ['Near the box.', 'Near a box.']],
  ['John is near a box. Mark is near a house. Where is Mark?', ['Near the house.', 'Near a house.']],
  ['John is under a box. Mark is under a house. Where is John?', ['Under the box.', 'Under a box.']],
  ['John is under a box. Mark is under a house. Where is Mark?', ['Under the house.', 'Under a house.']],
  ['John is above a box. Mark is above a house. Where is John?', ['Above the box.', 'Above a box.']],
  ['John is above a box. Mark is above a house. Where is Mark?', ['Above the house.', 'Above a house.']],
  ['A car is in a box and in a house. Where is the car?', ['In the house and in the box.', 'In a box and in a house.', 'In a house.', 'In a box.']],
  ['A car was in a box and in a house. Where was the car?', ['In the house and in the box.', 'In a box and in a house.', 'In a box.', 'In a house.']],
  ['John is in the box and in the red house. Where is John?', 'In the box and in the red house.'],

  # -- conjunction in location --

  ['John is in a box and house. Mark is near the house. Where is John?', ['In the house and in the box.', 'In a box and house.', 'In a box.']],
  ['John is in a box and house. Mark is near the house. Where is Mark?', 'Near the house.'],

  # -- containment and transitivity --

  ["""Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. Tallinn is in what?""", ['Earth, Europe and Estonia.', 'Estonia.', 'Europe.', 'Earth.']],
  ["""Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. What is not in Estonia?""", 'Riga.'],
  ["""Tallinn is in Estonia. Estonia is not outside Europe. Earth contains Europe.
       Estonia contains Tartu. Riga is not in Estonia. Riga is in Estonia?""", False],

  ['"Riga is outside America. Riga is not in what?', 'America.'],
  ['"Riga is not in America. What is not in America?', 'Riga.'],

  # -- spatial rules --

  ["""If a city is in Estonia, it is an Estonian city. Tallinn is in Estonia. Tallinn is a city.
     What is an Estonian city?""", 'Tallinn.'],
  ["""Cities in Estonia are estonian. Tallinn is in Estonia. Tallinn is a city.
    What is an Estonian city?""", 'Tallinn.'],

  # -- spatial conditionals --

  ['If John is in a box, he is in the house. John is in the box. Mark is not in the box. Where is John?', ['In the box and in the house.', 'In the house.', 'In the box.']],
  ['If a car is in a box, the car is in the house. A red car is in the box. Where is a car?', ['In the box and in the house.', 'In the house.', 'In the box.']],
  ['John is not in the box. John is in the red house. Where is John?', 'In the red house.'],
  ['The black car is not in the box. The car is in the red house. Where is the car?', 'In the red house.'],
  ['John is in a box. John is near a spoon. John is on the floor. Where is John?', ['Near the spoon, in the box and on the floor.', 'In a box.', 'On the floor.', 'Near a spoon.', 'In a box on the floor.']],
  ['John is in a box. John is near a spoon. John is on the floor. John is not in the box. Where is John?', ['On the floor and near the spoon.', 'On the floor.']],
  ['John is in a box. John is near a spoon. John is on the floor. John is not in a box. Where is John?', ['On the floor and near the spoon.', 'On the floor.', 'Near a spoon.']],

  # -- chained location --

  ["""John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the black car?""", ['In the street and in Tallinn.', 'In the street.', 'In Tallinn.']],
  ["""John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the red car?""", 'In the house.'],
  ["""John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is a car?""", ['In the house, in the street and in Tallinn.', 'In the house.', 'In the street.', 'In the house and in the street.', 'In Tallinn.']],
  ["""John is in a red car. John is a man. The red car is in the house. The black car is in the street.
      The street is in Tallinn. Where is the man?""", ['In the red car and in the house.', 'In the house.', 'In the red car.']],

  # -- nested location --

  ['John is in the box which is in the red house. Where is John?', ['In the box and in the red house.', 'In the red house.', 'In the box.']],
  ['John is in the box which is in the red house. Where is the box?', 'In the red house.'],

  ['John is in the box which is near the red house. Where is John?', ['In the box.', 'Near the red house.', 'In the box near the red house.']],
  ['John is in the box which is near the red house. Where is the box?', 'Near the red house.'],
  ['John is in the box near the red house. Where is John?', ['In the box.', 'In the box near the red house.']],

  ['John is in the box in the red house. Where is John?', ['In the box and in the red house.', 'In the box in the red house.', 'In the box.', 'In the red house.']],
  ['John is in the box near the red house. Where is the box?', 'Near the red house.'],

  ['John is in the box at the red house. A box is at a house?', True],
  ['John is in the box at a red house. The box is at a house?', True],
  ['John is in the box at a red house. The red box is at a house?', None],
  ['John is in the box at a red house. The box is at a blue house?', None],
  ['John is in a box at the red house. A box is at a house?', True],
  ['John is in a box at the red house. The box is at a house?', True],
  ['John is in a box at the red house. A box is at the red house?', True],

  # -- location of general terms --

  ['Birds are in the box. Where are birds?', 'In the box.'],
  ['The birds are in the box. Where are the birds?', 'In the box.'],
  ['The birds are in the box. Where are birds?', 'In the box.'],

  ['Birds near Tallinn are nice. John is near Tallinn. What is near Tallinn?', ['A bird near Tallinn', 'John.', 'John and birds.']],
  ['Birds near Tallinn are nice. John is near Tallinn. Who is near Tallinn?', 'John'],
  ['Birds near Tallinn are nice. John is near Tallinn. What is nice?', 'A bird near Tallinn'],
  ['Birds near Tallinn are nice. John is near Tallinn. John is a bird. Who is nice?', 'John'],

  ['Birds near Tallinn are nice. John is a bird who is near Tallinn. Who is nice?', 'John'],

  # -- location of actions --

  ['John ate candy in a house. John ate meat in a room. Where did John eat candy?', 'In a house'],
  ['John ate candy in a house. John ate meat in a room. Where did John eat meat?', 'In a room'],
  ['John ate candy in a house. John ate meat at a room. Where did John eat?', ['At a room and in a house', 'In a house and at a room.', 'In a house.', 'At a room.']],

  ['John jumped high in a room. John jumped low near the garage. Where did John jump?', ['In a room and near the garage', 'In a room.', 'Near the garage.']],
  ['John jumped high in a room. John jumped low near the garage. Where did John jump high?', 'In a room'],
  ['John jumped high in a room. John jumped low near the garage. Where did John jump low?', 'Near the garage'],
  ['John jumped high in a room. John jumped low near the garage. Where did John jump quickly?', None],

  # -- location via relative clause --

  ['Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate?', True],
  ['Bears ate berries in a forest which was seen by Mary. Mary saw the forest where the bears ate?', True],

  ['Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears drank?', None],
  ['Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate berries?', True],
  ['Bears ate berries in a forest which was bought by Mary. Mary bought the forest where the bears ate honey?', None],

  ['John lives in a red car bought by Mary. Mary bought the car where John lives?', True],
  ['John lives in a red car bought by Mary. Mary bought the car where John ate?', None],
  ['John lives in a red car bought by Mary. Mary bought the car where Mike lives?', None],

  # -- temporal-spatial --

  ['During 1800, John jumped in a house. During 1800, John jumped?', True],
  ['During 1800, John jumped in a house. During 1801, John jumped?', None],
  ['During 1800, John jumped in a house. When did John jump?', ['During the year 1800', 'During 1800.']],
  ['During 1800, John jumped in a house. Where did John jump?', 'In a house'],

  ['Before 1900, John jumped in a house. When did John jump?', ['Before the year 1900', 'Before 1900.']],
  ['Before 1900, John jumped in a house. After 1902, John ate in a house. When did John jump?', ['Before the year 1900', 'Before 1900.']],
  ['Before 1900, John jumped in a house. After 1902, John sat in a house. When did John sat?', ['After the year 1902', 'After 1902.']],
  ['On Monday, John jumped in a house. Where did John jump?', 'In a house'],
  ['On Monday, John jumped in a house. When did John jump?', 'On Monday'],
  ['The cat slept on the velvet sofa. Where did the cat sleep?', ['On the velvet sofa.', 'On the sofa.']],

  ['The book that Mary bought is on the table. Where is the book?', 'On the table.'],
  ['The cake that was on the counter has disappeared. Where was the cake?', 'On the counter.'],
  ['The cat sat on the mat and purred. Where did the cat sit?', 'On the mat.'],

# == ACTION AND WORLD STATE SEQUENCES ==

  # -- bAbI: single supporting fact --

  ['John travelled to the hallway. Mary journeyed to the bathroom. Where is John?', ['hallway', 'In the hallway.']],

  ['John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. Where is Mary?', ['bathroom', 'In the bathroom.']],
  ['John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Where is Sandra?', ['kitchen', 'In the kitchen.']],
  ['John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Sandra travelled to the hallway. John went to the garden. Where is Sandra?', ['hallway', 'In the hallway.']],
  ['John travelled to the hallway. Mary journeyed to the bathroom. Daniel went back to the bathroom. John moved to the bedroom. John went to the hallway. Sandra journeyed to the kitchen. Sandra travelled to the hallway. John went to the garden. Sandra went back to the bathroom. Sandra moved to the kitchen. Where is Sandra?', ['kitchen', 'In the kitchen.']],

  # -- bAbI: multi-step tracking --

  ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Where is Sandra?', ['hallway', 'In the hallway.']],
  ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Where is Sandra?', ['garden', 'In the garden.']],
  ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Where is Daniel?', ['hallway', 'In the hallway.']],
  ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. Where is Sandra?', ['office', 'In the office.']],
  ['Sandra travelled to the kitchen. Sandra travelled to the hallway. Mary went to the bathroom. Sandra moved to the garden. Sandra travelled to the office. Daniel journeyed to the hallway. Daniel journeyed to the office. John moved to the hallway. John travelled to the bathroom. John journeyed to the office. Where is Daniel?', ['office', 'In the office.']],

  ['The dog was barking and the cat was too. Was the cat barking?', True],
  ['Eve planned to travel. Eve traveled?', None],



# == QUESTION LOGIC (WHO/WHAT/WHICH) ==

  ['John is nice. Is it true that John is nice?', True],
  ['John is nice. Is it false that John is nice?', False],

  # -- who-is identity questions --

  ['John Sweeney is a car. John Smith is bad. Who is John Sweeney?', 'A car.'],

  ['John Sweeney is a car. Who is John?', ['John Sweeney is a car.', 'A car.', 'John Sweeney.']],
  ['John Sweeney is not a car. Who is John?', None],
  ['John Sweeney is a car. Who is Mary?', None],

  ['John Sweeney is cool and bought a car. John is a bad baby man. John is not big. Who is John?', ['John Sweeney is a not big cool bad baby man.', 'John Sweeney.']],

  # -- what/who/whom-of questions --

  ['Ellen is afraid of John. What is Ellen afraid of?', 'John'],
  ['Ellen is afraid of John. Who is Ellen afraid of?', 'John'],
  ['Ellen is afraid of John. Whom is Ellen afraid of?', 'John'],
  ['Ellen is afraid of John. Ellen is afraid of whom?', 'John'],
  ['Ellen is afraid of John. Ellen is afraid of who?', 'John'],

  ['Ellen is fond of John. Who is Ellen afraid of?', None],
  ['Ellen is fond of John. Whom is Ellen afraid of?', None],
  ['Ellen is fond of John. Ellen is afraid of who?', None],

  # -- multi-entity who/what questions --

  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man has an apple?""", 'John'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which has a pear?""", 'Mike'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which is bad?""", 'Greg'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man has a potato?""", None],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man is nice?""", 'John and Mike'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which man is bad?""", 'Greg'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has a pear?""", 'Mike'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which bad man has a pear?""", None],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has an apple or a pear?""", 'John and Mike'],
  ["""John is a nice man. John has an apple. Mike is a nice man. Greg is a bad man. Mike has a pear.
      Which nice man has an apple and a pear?""", None],

  ["""Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which animal can fly?""", 'A squirrel'],
  ["""Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which animal cannot fly?""", 'A fox'],
  ["""Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which can fly?""", 'A squirrel'],
  ["""Squirrels can fly. Foxes cannot fly. Squirrels and foxes are animals.
      Which table can fly?""", None],

# == IF-THEN INFERENCE ==

  # -- basic if-then --

  ['If cars are red, elephants are nice. Cars are red. Elephants are nice?', True],
  ['If cars are red, elephants are nice. Elephants are nice?', None],
  ['If some cars are red, elephants are nice. John is a red car. Elephants are nice?', True],
  ['If cars are green, elephants are nice. If elephants are nice, squirrels are red. Cars are green. Squirrels are red?', True],
  ['If cars have roofs, elephants are nice. Cars have roofs. Elephants are nice?', True],
  ['If cars have roofs, elephants are nice. John is a car. John has a roof. Elephants are nice?', None],
  ['If some cars have roofs, elephants are nice. John is a car. John has a roof. Elephants are nice?', True],
  ['If some car has a roof, elephants are nice. John is a car. John has a roof. Elephants are nice?', True],

  # -- if-then with variables --

  ['If X is cool then X is red. John is cool. Mike is red?', None],
  ['If X is cool then X is red. John is cool. John is red?', True],

  ['If X is cool and X is nice then X is red. John is nice and cool. John is red?', True],
  ['If X is cool and nice then X is red. John is nice and cool. John is red?', True],
  ['If X is cool and X is nice then X is red. Mike is nice. Mike is red?', None],

  ['If X is cool and X is nice then X is red. Mike is cool. Mike is red?', None],

  ["""If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike and Mary.
      Who is a child of John?""", 'Mike and Mary'],
  ["""If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike, Mary and Eve.
      Who is a child of John?""", 'Mike, Mary and Eve'],
  ["""If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike or Mary.
      Who is a child of John?""", 'Mike or Mary'],

  ['If X1 is a grandfather of Y1, Y1 is not a child of X1. John is a grandfather of Mike. Who is not a child of John?', 'Mike.'],
  ['If X1 is not a parent of Y1, Y1 is not a child of X1. John is not a parent of Mike. Who is not a child of John?', 'Mike.'],

  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John. Luke is a grandfather of Mike?""", True],
  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1. Mike is a grandchild of Luke?""", True],
  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike is male. Mike is a grandson of Luke?""", True],
  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike and Mickey are male. Who is a grandson of Luke?""", 'Mike and Mickey.'],
  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike and Mickey are not female. Any person is male or female.
      Who is a grandson of Luke?""", ['Mickey and Mike.', 'Mike and Mickey.']],
  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike or Mickey is not female. Any person is male or female.
      Who is a grandson of Luke?""", 'Mike or Mickey.'],
  ["""If X1 is a father of Y1, Y1 is a child of X1.
      If X1 is a father of Y1 and Y1 is a father of Z1, X1 is a grandfather of Z1.
      John is a father of Mike and Mickey. Luke is a father of John.
      If X1 is a grandfather of Y1, Y1 is a grandchild of X1.
      If X1 is male and X1 is a grandchild of Y1, X1 is a grandson of Y1.
      Mike or Mickey are not female. Any person is male or female.
      Who is a grandson of Luke?""", 'Mike or Mickey.'],

  ["""If an animal is cool and defeated then it is green.
   John is a cool defeated animal.
   Mike is an animal. Mike is cool. John is green?""", True],
  ["""If an animal is cool and defeated then it is green.
   John is a cool defeated animal.
   Mike is an animal. Mike is cool. John is not green?""", False],
  ["""If an animal is cool and defeated then it is green.
   John is a defeated animal.
   Mike is an animal. Mike is cool. John is green?""", None],

  ["""If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals.
    John is badly defeated. John is weak?""", True],
  ["""If someone is a nice animal and badly defeated then they are weak. John and Mike are nice animals.
    John is badly defeated. Mike is weak?""", None],
  ["""If someone is a nice animal and badly defeated then they are weak. John is a nice animal.
    Mike is badly defeated. Mike is weak?""", None],

  ["""If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. John is green?""", True],
  ["""If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. Who is green?""", 'John'],
  ["""If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. John is not green?""", False],
  ["""If an animal is cool and defeated then it is green.
   John is an animal. John is cool.
   Mike is an animal. Mike is cool. John is defeated. Mike is green?""", None],

  ['If someone is a bird and wounded then they are abnormal. John is wounded. John is a bird. John is abnormal?', True],
  ['If someone is a bird and wounded then they are abnormal. John is a bird. John is abnormal?', None],

  # -- have in if-then rules --

  ["""If an animal has a trunk, it is an elephant. John has a long trunk. John is an animal.
      John is an elephant?""", True],
  ['If an animal or bird has a tail, it is cute. John has a tail. John is cute?', None],
  ['If an animal or bird has a tail, it is cute. John is an animal. John has a tail. John is cute?', True],
  ['If an animal or bird has a tail, it is cute. John is a bird. John has a tail. John is cute?', True],
  ['If an animal or bird has a tail, it is cute. John is a bird or an animal. John has a tail. John is cute?', True],
  ['If a bear is nice, it has a tail. John is a nice bear. John has a tail?', True],
  ['If a big bear is nice, it has a tail. John is a nice bear. John has a tail?', None],
  ['If a bear is nice and has a trunk, it has a tail. John is a nice bear. John has a trunk. John has a tail?', True],
  ['If the bear is strong, the fox is nice. The bear is strong. Who is nice?', 'The fox.'],
  ['If the bear is strong, the fox is nice. The bear is strong. John is a fox. Who is nice?', ['The fox.', 'John.']],

  # -- coordination in conditionals --

  ['If animal or bird is nice and simple, it is cute. John is cute?', None],
  ['If animal or bird is nice and simple, it is cute. John is a nice and simple animal. John is cute?', True],
  ['If animal or bird is nice and simple, it is cute. John is a nice and simple bird. John is cute?', True],
  ['If animal or bird is nice and simple, it is cute. John is a nice animal. John is cute?', None],

  ['If a bear who is big is strong, it is nice. John is a big strong bear. John is nice?', True],
  ['If a bear who is big is strong, it is nice. John is a big bear. John is strong. John is nice?', 'Likely true'],

  ['If a bear who eats fish is strong, it is nice. John is a bear. John eats fish. John is strong. John is nice?', 'Likely true'],
  ['If a bear who eats fish is strong, it is nice. John is a bear. John eats carrots. John is strong. John is nice?', None],
  ['If a bear who eats fish is strong, it is nice. John is a bear. John eats fish. John is nice?', None],

  ['If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats strong fish. John is white. John is nice?', True],
  ['If a big bear who eats strong fish is white, it is nice. John is a bear. John eats strong fish. John is white. John is nice?', None],
  ['If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats strong fish. John is nice?', None],
  ['If a big bear who eats strong fish is white, it is nice. John is a big bear. John eats yellow fish. John is white. John is nice?', None],

  # -- if-then with family relations --

  ['If X1 is a father of Y1, Y1 is a child of X1. John is a father of Mike. Who is a child of John?', 'Mike.'],

  ['If John is not very big, John is nice. John is big. John is nice?', None],
  ['If John is not very big, John is nice. John is very big. John is nice?', None],
  ['If a bear is not very big, it is nice. John is a big bear. John is nice?', None],
  ['If a bear is not very big, it is nice. John is a very big bear. John is nice?', None],

# == DEFAULT & DEFEASIBLE REASONING ==

  # -- basic defaults with exceptions --

  ['Penguins are birds who do not fly. Birds fly. John is a penguin. John flies?', False],
  ['Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John flies?', False],
  ['Penguins are birds who do not fly. Birds fly. John is a bird. John flies?', True],
  ['Penguins are birds. Penguins do not fly. Birds fly. John is a bird. John flies?', True],
  ['Cars are nice. Cars are not nice?', False],

  ['Red cars are not nice. Cars are nice. Cars are not nice?', False],
  ['Red cars are not nice. Cars are nice. Red cars are not nice?', True],
  ['Red cars are not nice. Cars are nice. What are nice?', ['A car.', 'Non-red cars.']],
  ['Red cars are not nice. Cars are nice. What are not nice?', 'A red car.'],

  ['Red cars do not have trunks. Cars have trunks. Cars have trunks?', True],
  ['Red cars do not have trunks. Cars have trunks. Red cars have trunks?', False],
  ['Red cars do not have trunks. Cars have trunks. Cars have a trunk?', True],
  ['Red cars do not have trunks. Cars have trunks. Red cars have a trunk?', False],

  ['Red cars do not have trunks. Cars have a trunk. Cars have a trunk?', True],
  ['Red cars do not have trunks. Cars have trunks. John is a car. John has a trunk?', True],
  ['Red cars do not have trunks. Cars have trunks. John is a red car. John has a trunk?', False],

  # -- Tweety triangle --

  ['Penguins are birds. Penguins do not fly. Birds fly. Birds fly?', True],
  ['Penguins are birds. Penguins do not fly. Birds fly. Penguins fly?', False],
  ['Penguins are birds. Penguins do not fly. Birds fly. Who flies?', 'A bird.'],
  ['Penguins are birds. Penguins do not fly. Birds fly. Who does not fly?', 'A penguin.'],
  ['Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John is a bird?', True],
  ['Penguins are birds. Penguins do not fly. Birds fly. Mike is a bird. Mike is a penguin?', None],

  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    John does not fly?""", True],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    Mike flies?""", True],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.
    John runs?""", None],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who does not fly?""", 'John.'],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies?""", 'Mike and Eve.'],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who eats?""", ['John, Mike and Eve.', 'John, Mike, and Eve.', 'Mike and Eve.']],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies and eats?""", 'Mike and Eve.'],
  ["""Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike and Eve are birds.
    Who flies or eats?""", 'John, Mike and Eve.'],
  ["""Birds fly and eat. Baby birds do not fly. John is perhaps a baby.
     Mike and Eve and John are birds. Who flies and eats?""", ['Mike, Eve and likely John', 'Mike and Eve.']],

  ["""Bears eat berries. Baby bears do not eat berries. John is a bear.
     John eats berries?""", True],
  ["""Bears eat berries. Baby bears do not eat berries. John is a baby bear.
     John eats berries?""", False],
  ["""Bears eat berries. Baby bears eat no berries. John is a baby bear.
     John eats berries?""", False],
  ["""Bears eat berries. Baby bears do not eat berries. John and Mike are bears.
      John is a baby bear.
      Who eats berries?""", 'Mike.'],

  ["""Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds.
      Who can fly?""", 'Mike and Eve.'],
  ["""Birds can fly. Baby birds can not fly. John is a baby bird. Mike and Eve are birds.
      Who can not fly?""", 'John.'],
  ["""Bears can eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who can eat berries?""", 'Mike.'],
  ["""Bears can eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who can not eat berries?""", 'John.'],

  ['Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  ['Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John flies?', False],
  ['Birds can fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  ['Birds fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],
  ['Birds fly. No penguin can fly. Penguins are birds. John is a bird. John flies?', True],
  ['Birds can fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],

  ['Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who flies?', 'Mike'],
  ['Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who does not fly?', 'John'],
  ['Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who can fly?', 'Mike'],
  ['Birds fly. Baby birds can not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John'],

  ["""Bears eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who eats berries?""", 'Mike.'],
  ["""Bears eat berries. Baby bears can not eat berries. John and Mike are bears.
      John is a baby bear.  Who does not eat berries?""", 'John.'],
  ['Birds can fly. Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John.'],
  ["""Bears can eat berries. Baby bears do not eat berries. John and Mike are bears.
      John is a baby bear.  Who can not eat berries?""", 'John.'],
  ['Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', ['Perhaps John.', 'John.']],

  ['John is a car. John is bad. Who is John?', ['John is a bad car.', 'A car.']],
  ['John is a car. John is bad. Who is John?', ['John is a bad car.', 'A car.']],
  ['John is not a car. John is bad. Who is John?', 'John is bad.'],

  ["""Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Mike is big?""", True],
  ["""Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. John is big?""", False],
  ["""Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Who is big?""", 'Mike.'],
  ["""Elephants are big. Young elephants are not big.
      Mike is an elephant. John is a young elephant. Who is not big?""", 'John.'],
  ["""Elephants are big. Young elephants are not big.
      Who is big?""", ['An elephant.', 'Elephants that are not young.']],
  ["""Elephants are big. Young elephants are not big.
      Who is not big?""", 'A young elephant.'],

# == DEFAULTS WITH EXCEPTIONS (BLOCKING) ==

  # -- default do-actions --

  ['Bears eat berries. John is a bear. John eats berries?', True],
  ['Bears eat berries. John is a bear. John eats some berries?', True],
  ['Bears eat berries. John is a bear. John eats all berries?', None],
  ['Bears eat all berries. John is a bear. John eats all berries?', True],
  ['Some bears eat all berries. John is a bear. John eats berries?', None],

  ['Some bears eat all berries. Some bears eat berries?', True],

  # -- blocking in conditionals --

  ["""If a bear eats red berries, it is big. John eats berries. John is a bear.
     John is big?""", None],
  ["""If a bear eats red berries, it is big. John eats red berries. John is a bear.
     John is big?""", True],
  ['If X1 eats berries, it is a bear. John eats red berries. John is a bear?', True],

  # -- default disjunctive actions --

  ['Birds fly or swim. John is a bird. John does not fly. John swims?', True],
  ['Birds fly or swim. John is a bird. John swims?', None],
  ['Birds fly or do not swim. John is a bird. John does not fly. John swims?', False],
  ['Birds fly or do not swim. John is a bird. John never flies. John swims?', False],
  ['Birds fly and swim. John is a bird. John swims and flies?', True],

# == UNCERTAINTY & CONFIDENCE ==

  # -- adverbial probability --

  ['Elephants are probably animals. John is an elephant. John is an animal?', 'Probably true.'],
  ['Elephants are rarely animals. John is an elephant. John is an animal?', 'Probably false.'],
  ['Probably elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  ['Probably elephants are not animals. John is an elephant. John is an animal?', 'Probably false.'],

  # -- sentence-initial probably --

  ['Probably elephants have long trunks. John is an elephant. John has a trunk?', 'Probably true.'],
  ['Probably elephants have no trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  ['Elephants have probably long trunks. John is an elephant. John has a long trunk?', 'Probably true.'],
  ['Elephants have probably no trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  ['Elephants have rarely trunks. John is an elephant. John has a trunk?', 'Probably false.'],
  ['It is true that elephants have long grey trunks. John is an elephant. Who has a trunk?', 'John.'],
  ['It is false that elephants have long grey trunks. John is an elephant. Who has a trunk?', None],
  ['It is probably true that elephants have long grey trunks. John is an elephant. Who has a trunk?', ['Probably John.', 'John.']],
  ["""It is probable that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  ["""It is probable that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably false.'],
  ["""It is probably true that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  ["""It is probably false that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  ["""It is unlikely that if X1 is a grandfather of Y1, Y1 is a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably false.'],
  ["""It is unlikely that if X1 is a grandfather of Y1, Y1 is not a child of X1. John is grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  ["""It is probable that if X1 is not a grandfather of Y1, Y1 is a child of X1. John is not a grandfather of Mike.
       Mike is a child of John?""", 'Probably true.'],
  ['Tallinn is probably in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  ['Tallinn is hardly in Latvia. Tallinn is in Latvia?', 'Likely false.'],
  ['It is true that Tallinn is in Estonia. Tallinn is in Estonia?', True],
  ['It is false that Tallinn is in Latvia. Tallinn is in Latvia?', False],
  ['It is probably true that Tallinn is in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  ['It is probably false that Tallinn is in Latvia. Tallinn is in Latvia?', 'Probably false.'],
  ['Probably Tallinn is in Estonia. Tallinn is in Estonia?', 'Probably true.'],
  ['It is not probable that Tallinn is in Latvia. Tallinn is in Latvia?', 'Probably false.'],

  # -- it is true/false that --

  ['It is true that elephants are animals. John is an elephant. John is an animal?', True],
  ['It is false that elephants are animals. John is an elephant. John is an animal?', False],
  ['It is not true that elephants are animals. John is an elephant. John is an animal?', False],
  ['It is not false that elephants are animals. John is an elephant. John is an animal?', True],
  ['It is probably true that elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  ['It is probably false that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  ['It is probable that elephants are animals. John is an elephant. John is an animal?', 'Probably true.'],
  ['It is not probable that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  ['It is unlikely that elephants are animals. John is an elephant. John is an animal?', 'Probably false.'],
  ['It is true that John is a child of Mike. John is a child of Mike?', True],
  ['It is false that John is a child of Mike. John is a child of Mike?', False],

  # -- it is probable/improbable that --

  ['It is probable that John is a child of Mike. John is a child of Mike?', 'Probably true.'],
  ['It is probably true that John is a child of Mike. John is a child of Mike?', 'Probably true.'],
  ['It is improbable that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  ['It is not probable that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  ['It is unlikely that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  ['It is probably false that John is a child of Mike. John is a child of Mike?', 'Probably false.'],
  ['John is probably a child of Mike. John is a child of Mike?', 'Probably true.'],
  ['Probably John is a child of Mike. John is a child of Mike?', 'Probably true.'],

  # -- negated universals --

  ['It is not true that all big yellow cats are strong. Some yellow cats are not strong?', True],
  ['It is not true that all big yellow cats are strong. Some red cats are not strong?', None],
  ['It is not true that some big yellow cats are strong. All big yellow cats are not strong?', True],

  ['John is nice. It is true that John is nice?', True],
  ['John smokes tobacco with a probability 0.8. What does John smoke?', ['Likely a tobacco', 'Tobacco.']],
  ['John smokes tobacco with a probability 0.8. John smokes?', 'Likely true'],
  ['John smokes tobacco with a probability 80 percent. Does John smoke?', 'Likely true'],
  ['John is a man. John is probably not bad. Who is John?', ['John is a not bad man.', 'A man.']],
  ["""Birds fly and eat. Baby birds do not fly. John is hardly a baby bird.
     Mike and Eve and John are birds. Who flies and eats?""", ['Mike, Eve and John', 'Mike, Eve, and John.']],
  ["""Birds fly and eat. Baby birds do not fly. John is probably a baby bird.
     Mike and Eve and John are birds. Who flies and eats?""", 'Mike and Eve'],

  # -- explicit percentage probability --

  ['John is an elephant with a probability 100 percent. John is an elephant?', True],
  ['John is an elephant with a probability 0 percent. John is an elephant?', False],
  ['John is an elephant with a probability 10 percent. John is an elephant?', 'Likely false.'],
  ['John is an elephant with a probability 90 percent . John is an elephant?', 'Likely true.'],
  ['John is an elephant with a probability 50 percent. John is an elephant?', None],

  ['Tallinn is in Estonia with a probability 90 percent. Tallinn is in Estonia?', 'Likely true.'],
  ['Tallinn is in Latvia with a probability 10 percent. Tallinn is in Latvia?', 'Likely false.'],
  ['Tallinn is in Latvia with a probability 50 percent. Tallinn is in Latvia?', None],

  ['Elephants have a trunk with a probability 90 percent. John is an elephant. John has a trunk?', 'Likely true.'],
  ['Elephants have a trunk with a probability 10 percent. John is an elephant. John has a trunk?', 'Likely false.'],
  ['Elephants have a trunk with a probability 50 percent. John is an elephant. John has a trunk?', None],
  ['Elephants have a trunk with a probability 90 percent. John is an elephant. Who has a trunk?', ['Likely John.', 'John.']],

  ['Elephants probably do not have wings. John is an elephant. Who does not have wings?', ['Probably John.', 'John.']],
  ['Elephants probably do not have wings. John is maybe an elephant. Who does not have wings?', 'Maybe John.'],
  ['John probably smokes. John smokes?', 'Probably true'],
  ['Probably John smokes. John smokes?', 'Probably true'],
  ['It is probably true that John smokes. John smokes?', 'Probably true'],

  # -- explicit decimal probability --

  ['John smokes with a probability 90%. John smokes?', 'Likely true'],
  ['John smokes with a probability 90 percent. John smokes?', 'Likely true'],
  ['John smokes with a probability 0.9. John smokes?', 'Likely true'],
  ['John smokes with a probability 0.1. John smokes?', 'Likely false'],
  ['John smokes tobacco with a probability 0.8. John smokes what?', ['Likely a tobacco', 'Tobacco.']],

  # -- probability with location --

  ['Probably John is in a cave. Where is John?', ['Probably in the cave', 'Probably in a cave.']],
  ['John is probably in a cave. Where is John?', ['Probably in the cave', 'Probably in a cave.', 'In a cave.']],

  ['John is in a cave with a probability 90%. Where is John?', 'Likely in the cave'],
  ['John is in a cave with a probability 10%. Where is John?', None],
  ['John is in a cave with a probability 10%. John is in the cave?', 'Likely false'],
  ['John is in a cave with a probability 10%. John is in a cave?', 'Likely false'],

# == ADVANCED SEMANTIC OPERATORS ==

  # -- implicative: manage --

  ['John managed to open the door. John opened the door?', True],
  ['John managed to open the door. John did not open the door?', False],
  ['Mary managed to solve the puzzle. Mary solved the puzzle?', True],

  # -- implicative: fail --

  ['Tom failed to catch the bus. Tom caught the bus?', False],
  ['Eve failed to finish the report. Eve finished the report?', False],

  # -- non-implicative: try --

  ['John tried to open the door. John opened the door?', None],
  ['Mary tried to solve the puzzle. Mary solved the puzzle?', None],

  # -- non-implicative: want --

  ['Tom wanted to leave. Tom left?', None],

  # -- promise --

  ['John promised to help Mary. John helped Mary?', None],

  # -- decide --

  ['Mary decided to leave. Mary left?', None],

  # -- refuse --

  ['Tom refused to eat the soup. Tom ate the soup?', False],
  ['Tom refused to eat the soup. Did Tom drink the soup?', None],

  # -- forget --

  ['Eve forgot to lock the door. Eve locked the door?', False],

  # -- raising: seem/appear --

  ['John seemed tired. John was energetic?', None],
  ['Mary appeared angry. Mary was not angry?', None],

  # -- passive raising --

  ['John was seen to enter the room. John entered the room?', True],
  ['John was seen to enter the room. Did John leave the room?', None],
  ['Mary was heard to sing. Mary sang?', True],

  # -- deontic modality --

  ['John must leave the room. Is John allowed to stay?', False],
  ['You may enter the building. Do you have permission to enter?', True],
  ['John might be in the kitchen. Is John definitely in the kitchen?', False],

  # -- focus particle: only --

  ['Only John bought a car. Did Mary buy a car?', False],
  ['Only John bought a car. Who bought a car?', 'John.'],
  ['John only eats apples. Does John eat bananas?', False],

  # -- exceptive --

  ['Everyone except John arrived. Did Mary arrive?', True],
  ['Everyone except John arrived. Did John arrive?', False],
  ['All the boxes are red except for the small one. Is the small box red?', False],

  # -- embedded interrogative --

  ['John knows who broke the vase. Does John know that the vase is broken?', True],
  ['Mary asked whether it was raining. Does Mary know if it is raining?', None],
  ['Tom found out where the key was. Does Tom know the location of the key?', True],

  # -- donkey anaphora --

  ['Every farmer who owns a donkey beats it. If John is a farmer and owns a donkey, does he beat it?', True],
  ['If a man has a coin, he puts it in the box. John has a coin. Where is the coin?', 'In the box.'],

  # -- degree complement: too --

  ['The box is too heavy for Mary to lift. Did Mary lift the box?', False],

  # -- causative --

  ['John made Mary cry. Did Mary cry?', True],
  ['Tom had the mechanic fix his car. Who fixed the car?', 'The mechanic.'],

  # -- cleft sentence --

  ['It was John who ate the cake. Who ate the cake?', 'John.'],
  ['It was the red car that won. Did the blue car win?', False],
  ['John and Mary lifted the piano together. Did John lift the piano alone?', False],
  ['John and Mary each bought an apple. How many apples were bought?', ['Two.', '2.']],

# == COMPLEX REASONING CHAINS ==

  # -- fear chains --

  ['Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is emily afraid of?', ['wolf', 'Gertrude.']],
  ['Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is winona afraid of?', ['mouse', 'Jessica.']],
  ['Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is gertrude afraid of?', ['mouse', 'Jessica.']],
  ['Wolves are afraid of mice. Sheep are afraid of mice. Winona is a sheep. Mice are afraid of cats. Cats are afraid of wolves. Jessica is a mouse. Emily is a cat. Gertrude is a wolf. What is jessica afraid of?', 'cat'],

  # -- extended fear chains --

  ['Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is emily afraid of?', 'sheep'],
  ['Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is jessica afraid of?', 'cat'],
  ['Cats are afraid of wolves. Mice are afraid of cats. Sheep are afraid of mice. Gertrude is a cat. Wolves are afraid of sheep. Jessica is a mouse. Emily is a wolf. Winona is a cat. What is gertrude afraid of?', 'wolf'],

  ["""Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Emily afraid of?""", ['Probably a wolf', 'Wolves.', 'Gertrude.']],
  ["""Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    Who is Emily afraid of?""", ['Probably Gertrude', 'Gertrude.', 'Wolves.']],
  ["""Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What are cats afraid of?""", ['Probably a wolf', 'Wolves.']],
  ["""Wolves are afraid of mice.
    Sheep are afraid of mice.
    Winona is a sheep.
    Mice are afraid of cats.
    Cats are afraid of wolves.
    Jessica is a mouse.
    Emily is a cat.
    Gertrude is a wolf.
    What is Winona afraid of?""", ['Probably a mouse', 'Mice.']],




]
