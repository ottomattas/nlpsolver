# Extended linguistic regression tests for the nlpsolver pipeline.
# Sources: Gemini and GPT suggestions (tests/suggested_examples.txt).
# Covers: argument structure, passive, coordination, ellipsis,
# relative clauses, modification, comparatives, anaphora, tense,
# appositives, participials, possessives, ditransitives, control verbs,
# temporal clauses, PP attachment, reflexives, and more.

[

  # --- 1. ARGUMENT STRUCTURE (Transitive, Ditransitive, Dative Shift) ---

  ["John gave Mary a book. Who received a book?", ["Mary."]],
  ["John gave Mary a book. Did John receive a book?", None],
  ["John gave a book to Mary. What did Mary receive?", ["A book.", "The book."]],
  ["John gave a book to Mary. Did Eve receive a book?", None],
  ["The chef cooked a meal for the guests. Who was the meal for?", ["The guests."]],
  ["The chef cooked a meal for the guests. Did the chef eat the meal?", None],
  ["The teacher showed the students the map. Who saw the map?", ["The students."]],
  ["The teacher showed the students the map. Did the teacher show a book?", None],
  ["The teacher showed the map to the students. What did the teacher show?", ["The map."]],
  ["Susan bought herself a new car. Who owns a new car?", ["Susan."]],
  ["Susan bought herself a new car. Did Tom buy a car?", None],
  ["Susan bought a new car for herself. What did Susan buy?", ["A new car.", "A car."]],

  # --- 2. PASSIVE VOICE (Direct and Indirect) ---

  ["The glass was broken by the boy. Who broke the glass?", ["The boy."]],
  ["The glass was broken by the boy. Did the girl break the glass?", None],
  ["The letter was written in June. Was the letter written?", [True]],
  ["The letter was written in June. Was the letter written in March?", None],
  ["Mary was given a promotion. Who received a promotion?", ["Mary."]],
  ["Mary was given a promotion. Did Mary receive a demotion?", None],
  ["A promotion was given to Mary. What did Mary get?", ["A promotion."]],
  ["The city was destroyed. Is the city destroyed?", [True]],
  ["The city was destroyed. Is the city intact?", False],
  ["The mouse was chased by the cat. Who was the cat chasing?", ["The mouse."]],
  ["The mouse was chased by the cat. Did the mouse chase the cat?", False],
  ["The bill was paid by John. Did John pay the bill?", [True]],
  ["The bill was paid by John. Did Mary pay the bill?", None],

  # --- 3. COORDINATION (NP, VP, and Clausal) ---

  ["John and Mary saw the movie. Did Mary see the movie?", [True]],
  ["John and Mary saw the movie. Did Mary see a play?", None],
  ["John and Mary saw the movie. Who saw the movie?", ["John and Mary."]],
  ["The cat sat on the mat and purred. Did the cat purr?", [True]],
  ["The cat sat on the mat and purred. Did the cat bark?", None],
  ["The cat sat on the mat and purred. Where did the cat sit?", ["On the mat."]],
  ["John ate an apple and drank some water. What did John drink?", ["Water.", "Some water."]],
  ["John ate an apple and drank some water. Did John eat a banana?", None],
  ["The students studied hard and passed the exam. Did the students pass the exam?", [True]],
  ["The students studied hard and passed the exam. Did the students fail the exam?", False],
  ["The dog barked and the cat ran away. What did the cat do?", ["Ran away."]],
  ["Either John or Bill went to the store. Did someone go to the store?", [True]],
  ["Either John or Bill went to the store. Did Mary go to the store?", None],

  # --- 4. ELLIPSIS & GAPPING ---

  ["John likes tea and Mary coffee. What does Mary like?", ["Coffee."]],
  ["John likes tea and Mary coffee. Does Mary like tea?", None],
  ["John went to Paris and Mary to London. Where did Mary go?", ["London.", "To London."]],
  ["John went to Paris and Mary to London. Did Mary go to Paris?", False],
  ["Paul ate a sandwich and Bill a salad. What did Bill eat?", ["A salad."]],
  ["Paul ate a sandwich and Bill a salad. Did Paul eat a salad?", None],
  ["John saw the doctor and Mary did too. Did Mary see the doctor?", [True]],
  ["John saw the doctor and Mary did too. Did Mary see the dentist?", None],
  ["The dog was barking and the cat was too. Was the cat barking?", [True]],
  ["John bought a book, and Bill said Peter did too. Did Bill say Peter bought a book?", [True]],
  ["If John wrote a report, then Bill did too. John wrote a report. Did Bill write a report?", [True]],
  ["If John wrote a report, then Bill did too. John wrote a report. Did Bill write a novel?", None],

  # --- 5. RELATIVE CLAUSES (Subject and Object) ---

  ["The man who saw John is tall. Who saw John?", ["The man."]],
  ["The man who saw John is tall. Did John see the man?", None],
  ["The man whom John saw is tall. Who did John see?", ["The man."]],
  ["The man whom John saw is tall. Is the man short?", False],
  ["The book that Mary bought is on the table. Where is the book?", ["On the table."]],
  ["The book that Mary bought is on the table. Who bought the book?", ["Mary."]],
  ["The book that Mary bought is on the table. Did John buy the book?", None],
  ["The car which John drove was red. What color was the car?", ["Red."]],
  ["The car which John drove was red. Was the car blue?", False],
  ["The student who passed the test studied a lot. Did the student study?", [True]],
  ["The student who passed the test studied a lot. Did the student fail the test?", False],
  ["The cake that was on the counter has disappeared. Where was the cake?", ["On the counter."]],

  # --- 6. ADJUNCTS & MODIFICATION (Manner, Temporal, Locative) ---

  ["John ate the apple quickly. How did John eat the apple?", ["Quickly."]],
  ["John ate the apple quickly. Did John eat a banana?", None],
  ["The cat slept on the velvet sofa. Where did the cat sleep?", ["On the velvet sofa.", "On the sofa."]],
  ["The cat slept on the velvet sofa. Did the cat sleep on the floor?", False],
  ["Mary visited London in September. When did Mary visit London?", ["In September."]],
  ["Mary visited London in September. Did Mary visit Paris?", None],
  ["The blue bird sang a beautiful song. What color was the bird?", ["Blue."]],
  ["The blue bird sang a beautiful song. Was the bird red?", False],
  ["The tall man walked into the small room. Who walked into the room?", ["The tall man.", "The man."]],
  ["John works at the hospital every day. Where does John work?", ["At the hospital."]],
  ["John works at the hospital every day. Does John work at the school?", None],
  ["The old wooden bridge collapsed yesterday. What happened to the bridge?", ["It collapsed."]],

  # --- 7. BASIC COMPARATIVES (Inequality and Equality) ---

  ["The red car is faster than the blue car. Is the blue car faster than the red car?", [False]],
  ["The red car is faster than the blue car. Is the green car faster than the red car?", None],
  ["John is as tall as Bill. Is John taller than Bill?", [False]],
  ["John is as tall as Bill. Is John's height equal to Bill's?", [True]],
  ["The mountain is higher than the hill. Which is lower, the mountain or the hill?", ["The hill."]],
  ["The mountain is higher than the hill. Is the hill higher than the mountain?", False],
  ["This book is more interesting than that one. Is 'that one' more interesting?", [False]],

  # --- 8. ANAPHORA & COREFERENCE ---

  ["John saw himself in the mirror. Who did John see?", ["John.", "Himself."]],
  ["John saw himself in the mirror. Did Mary see John in the mirror?", None],
  ["Mary said that she was tired. Who was tired?", ["Mary."]],
  ["Mary said that she was tired. Was Mary happy?", None],
  ["The boy lost his backpack. Who does the backpack belong to?", ["The boy."]],
  ["The boy lost his backpack. Did the boy find his backpack?", None],
  ["The students brought their books. Whose books were they?", ["The students'.", "The students."]],
  # Note: "John told Bill that he should leave" is ambiguous — either answer is acceptable
  ["John told Bill that he should leave. Who should leave?", ["Bill.", "John."]],

  # --- 9. TENSE & ASPECT ---

  ["John will go to the store tomorrow. Has John already gone to the store?", [False]],
  ["John has finished his homework. Is the homework finished?", [True]],
  ["John has finished his homework. Is the homework unfinished?", False],
  ["John has finished his homework. Has John finished his project?", None],
  ["Mary was reading a book when the phone rang. What was Mary doing?", ["Reading a book."]],
  ["Mary was reading a book when the phone rang. Did the doorbell ring?", None],
  ["The train leaves at noon. When does the train leave?", ["At noon."]],
  ["The train leaves at noon. Does the train leave at midnight?", False],

  # --- 10. PREPOSITIONAL AMBIGUITY (PP Attachment) ---

  # "The man saw the woman with a telescope" — either attachment is acceptable
  ["The man saw the woman with a telescope. Who had the telescope?", ["The man.", "The woman."]],
  ["John ate the pizza on the table. Where was the pizza?", ["On the table."]],
  ["John ate the pizza on the table. Was the pizza on the floor?", False],
  ["John ate the pizza on the table. Did John eat a sandwich?", None],
  ["The cat in the hat sat on the mat. Where was the cat?", ["In the hat.", "On the mat."]],
  ["Mary put the book on the shelf in the library. Where is the shelf?", ["In the library."]],
  ["Mary put the book on the shelf in the library. Did Mary put a magazine on the shelf?", None],


  # ====== GPT suggestions ======

  # appositives and titles

  ["John, a doctor, arrived. John is a doctor?", True],
  ["John, a doctor, arrived. John is a nurse?", None],
  ["Mary, a pilot, smiled. Who is a pilot?", "Mary."],
  ["Paul, a carpenter, carried a box. Paul carried a box?", True],
  ["Paul, a carpenter, carried a box. Paul is a plumber?", None],
  ["Anna, the manager, called Eve. Who is the manager?", "Anna."],
  ["The manager, Anna, called Eve. Anna is the manager?", True],
  ["The manager, Anna, called Eve. Eve is the manager?", False],
  ["John, my neighbor, owns a bicycle. John owns a bicycle?", True],
  ["My neighbor, John, owns a bicycle. Who is my neighbor?", "John."],
  ["Dr. Smith, a surgeon, entered the room. Dr. Smith is a surgeon?", True],
  ["Dr. Smith, a surgeon, entered the room. Dr. Smith is a dentist?", None],
  ["A surgeon, Dr. Smith, entered the room. Who entered the room?", "Dr. Smith."],
  ["Tom, a friend of Mary, laughed. Tom is a friend of Mary?", True],
  ["Tom, a friend of Mary, laughed. Mary is a friend of Tom?", None],
  ["Tom, a friend of Mary, laughed. Tom is a friend of Eve?", None],
  ["Sara, the sister of Mike, left. Sara is the sister of Mike?", True],
  ["Sara, the sister of Mike, left. Sara is the brother of Mike?", False],

  # participial modifiers: active and passive

  ["The man carrying a bag waved. The man carried a bag?", True],
  ["The man carrying a bag waved. The man carried a box?", None],
  ["The woman holding a lamp sang. The woman held a lamp?", True],
  ["The child wearing a hat ran. The child wore a hat?", True],
  ["The child wearing a hat ran. The child wore a coat?", None],
  ["The box containing apples fell. The box contained apples?", True],
  ["The box containing apples fell. The box contained oranges?", None],
  ["The letter written by Mary arrived. Mary wrote the letter?", True],
  ["The letter written by Mary arrived. Did John write the letter?", None],
  ["The cake baked by John was sweet. John baked the cake?", True],
  ["The cake baked by John was sweet. The cake was bitter?", False],
  ["The song sung by Eve was sad. Eve sang the song?", True],
  ["The dog chased by the boy escaped. The boy chased the dog?", True],
  ["The dog chased by the boy escaped. Did the dog catch the boy?", None],
  ["The woman admired by John smiled. John admired the woman?", True],
  ["The man standing by the door coughed. The man stood by the door?", True],
  ["The man standing by the door coughed. The man stood by the window?", None],
  ["The horse kept in the stable was calm. The horse was in the stable?", True],
  ["The car parked behind the house was blue. The car was behind the house?", True],
  ["The car parked behind the house was blue. The car was in front of the house?", False],
  ["The children playing in the garden laughed. The children were in the garden?", True],
  ["The children playing in the garden laughed. The children were in the kitchen?", None],
  ["The cup filled with water fell. The cup contained water?", True],
  ["The road leading to the village was narrow. The road led to the village?", True],
  ["The road leading to the village was narrow. The road was wide?", False],
  ["The tree growing near the river was tall. The tree grew near the river?", True],

  # participial + modifier interaction

  ["The man carrying a red bag waved. The bag was red?", True],
  ["The man carrying a red bag waved. The bag was blue?", False],
  ["The woman holding a heavy lamp sang. The lamp was heavy?", True],
  ["The woman holding a heavy lamp sang. The lamp was light?", None],
  ["The child wearing a small hat ran. The hat was small?", True],
  ["The letter written by Mary was long. Mary wrote a long letter?", True],
  ["The letter written by Mary was long. The letter was short?", False],
  ["The cake baked by John was sweet. John baked a sweet cake?", True],
  ["The cake baked by John was sweet. Did Mary bake the cake?", None],
  ["The dog chased by the boy was black. The boy chased a black dog?", True],
  ["The dog chased by the boy was black. The dog was white?", False],

  # nested possessives and possessive chains

  ["John's brother has a car. John's brother has a car?", True],
  ["John's brother has a car. John's sister has a car?", None],
  ["Mary's sister owns a house. Who owns a house?", "Mary's sister."],
  ["John's brother's car is red. John's brother has a car?", True],
  ["John's brother's car is red. John's brother's car is blue?", False],
  ["Mary's uncle's bicycle is blue. Mary's uncle has a bicycle?", True],
  ["Mary's uncle's bicycle is blue. Mary's aunt has a bicycle?", None],
  ["The roof of John's house is green. John has a house?", True],
  ["The handle of Mary's suitcase broke. Mary had a suitcase?", True],
  ["The handle of Mary's suitcase broke. Did the suitcase break?", None],
  ["The door of the house of John was open. John had a house?", True],
  ["The door of the house of John was open. Was the door closed?", False],
  ["The tail of the dog of Mary was short. Mary had a dog?", True],
  ["The color of John's car was black. John had a car?", True],
  ["The color of John's car was black. John had a truck?", None],
  ["The owner of the horse of Mike smiled. Mike had a horse?", True],
  ["The brother of the friend of Eve arrived. Eve had a friend?", True],
  ["The brother of the friend of Eve arrived. Did Eve's friend arrive?", None],
  ["John saw the mother of the boy. John saw a boy's mother?", True],

  # possessives with questions about the possessor

  ["John's sister laughed. Who has a sister?", "John."],
  ["John's sister laughed. Did John's brother laugh?", None],
  ["Mary's uncle arrived. Who has an uncle?", "Mary."],
  ["The bicycle of Tom was new. Who had a bicycle?", "Tom."],
  ["The bicycle of Tom was new. Was the bicycle old?", False],
  ["The toy of the child was broken. Who had a toy?", ["The child.", "A child."]],
  ["The toy of the child was broken. Was the toy intact?", False],

  # ditransitives and dative alternation

  ["John gave Mary a book. Mary got a book?", True],
  ["John gave Mary a book. Did Mary give John a book?", None],
  ["John gave a book to Mary. Mary got a book?", True],
  ["Eve sent Tom a letter. Tom got a letter?", True],
  ["Eve sent Tom a letter. Did Tom send Eve a letter?", None],
  ["Eve sent a letter to Tom. Who got a letter?", "Tom."],
  ["The teacher showed the students a map. The students saw a map?", True],
  ["The teacher showed the students a map. Did the students see a globe?", None],
  ["The teacher showed a map to the students. Who saw a map?", "The students."],
  ["Anna handed Mark a key. Mark got a key?", True],
  ["Anna handed a key to Mark. Anna handed Mark a key?", True],
  ["Anna handed a key to Mark. Did Anna hand Mark a lock?", None],
  ["John told Mary a story. Mary heard a story?", True],
  ["John told Mary a story. Did Mary tell John a story?", None],
  ["John told a story to Mary. Who heard a story?", "Mary."],
  ["The guide offered the tourists tea. The tourists got tea?", True],
  ["The guide offered the tourists tea. Did the guide offer coffee?", None],
  ["The guide offered tea to the tourists. Who got tea?", "The tourists."],

  # ditransitives with object identification

  ["John gave Mary a red book. Mary got a red book?", True],
  ["John gave Mary a red book. Mary got a blue book?", None],
  ["Eve sent Tom a long letter. Tom got a long letter?", True],
  ["Eve sent Tom a long letter. Tom got a short letter?", None],
  ["Anna handed Mark a silver key. Mark got a silver key?", True],
  ["The teacher showed the students a large map. The students saw a large map?", True],
  ["The teacher showed the students a large map. Did the students see a small map?", None],

  # passive with by-phrases

  ["The window was broken by John. John broke the window?", True],
  ["The window was broken by John. Did Mary break the window?", None],
  ["The song was sung by Mary. Mary sang the song?", True],
  ["The letter was written by Eve. Eve wrote the letter?", True],
  ["The letter was written by Eve. Did Tom write the letter?", None],
  ["The house was built by Tom. Tom built the house?", True],
  ["The house was built by Tom. Tom destroyed the house?", None],
  ["The bicycle was repaired by Anna. Anna repaired the bicycle?", True],
  ["The bicycle was repaired by Anna. Anna broke the bicycle?", None],
  ["The cake was eaten by the child. The child ate the cake?", True],
  ["The ball was kicked by Mike. Mike kicked the ball?", True],
  ["The ball was kicked by Mike. Did Mike catch the ball?", None],
  ["The tree was cut by the farmer. The farmer cut the tree?", True],
  ["The book was read by Sara. Sara read the book?", True],
  ["The book was read by Sara. Did Sara write the book?", None],
  ["The car was washed by Paul. Paul washed the car?", True],
  ["The room was cleaned by the maid. The maid cleaned the room?", True],
  ["The room was cleaned by the maid. Did the maid dirty the room?", False],
  ["The picture was painted by Leo. Leo painted the picture?", True],

  # passive without by-phrase: do not infer the agent

  ["The window was broken. John broke the window?", None],
  ["The letter was written. Mary wrote the letter?", None],
  ["The cake was eaten. Who ate the cake?", "Someone unknown."],
  ["The room was cleaned. Who cleaned the room?", "Someone unknown."],

  # control / implicative contrasts

  ["John managed to open the door. John opened the door?", True],
  ["John managed to open the door. John did not open the door?", False],
  ["Mary managed to solve the puzzle. Mary solved the puzzle?", True],
  ["Tom failed to catch the bus. Tom caught the bus?", False],
  ["Tom failed to catch the bus. Did Tom miss the bus?", None],
  ["Eve failed to finish the report. Eve finished the report?", False],
  ["John tried to open the door. John opened the door?", None],
  ["Mary tried to solve the puzzle. Mary solved the puzzle?", None],
  ["Tom wanted to leave. Tom left?", None],
  ["Eve planned to travel. Eve traveled?", None],
  ["John promised to help Mary. John helped Mary?", None],
  ["Mary decided to leave. Mary left?", None],
  ["Tom refused to eat the soup. Tom ate the soup?", False],
  ["Tom refused to eat the soup. Did Tom drink the soup?", None],
  ["Eve forgot to lock the door. Eve locked the door?", False],

  # raising-like and perception-like complements

  ["John seemed tired. John was tired?", True],
  ["John seemed tired. John was energetic?", None],
  ["Mary appeared angry. Mary was angry?", True],
  ["Mary appeared angry. Mary was not angry?", None],
  ["Tom was likely to win. Tom won?", None],
  ["Eve was certain to arrive. Eve arrived?", None],
  ["John was seen to enter the room. John entered the room?", True],
  ["John was seen to enter the room. Did John leave the room?", None],
  ["Mary was heard to sing. Mary sang?", True],

  # temporal subordinate clauses

  ["Before John left, he locked the door. John locked the door?", True],
  ["Before John left, he locked the door. John left?", True],
  ["Before John left, he locked the door. Did John lock the window?", None],
  ["After Mary arrived, she called Tom. Mary arrived?", True],
  ["After Mary arrived, she called Tom. Mary called Tom?", True],
  ["After Mary arrived, she called Tom. Did Mary call Eve?", None],
  ["When Eve entered the house, she smiled. Eve entered the house?", True],
  ["When Eve entered the house, she smiled. Eve did not enter the house?", False],
  ["When Eve entered the house, she smiled. Eve smiled?", True],
  ["While John was cooking, Mary read a book. John cooked?", True],
  ["While John was cooking, Mary read a book. Did John read a book?", None],
  ["While John was cooking, Mary read a book. Mary read a book?", True],
  ["As Tom walked home, it rained. Tom walked home?", True],
  ["As Tom walked home, it rained. It rained?", True],
  ["As Tom walked home, it rained. Did it snow?", None],
  ["Once Anna found the key, she opened the box. Anna found the key?", True],
  ["Once Anna found the key, she opened the box. Anna opened the box?", True],
  ["Once Anna found the key, she opened the box. Did Anna close the box?", None],
  ["Since Mike lost his ticket, he stayed outside. Mike lost his ticket?", True],
  ["Since Mike lost his ticket, he stayed outside. Mike stayed outside?", True],
  ["Since Mike lost his ticket, he stayed outside. Did Mike find his ticket?", None],
  ["Until Sara arrived, John waited. Sara arrived?", True],
  ["Until Sara arrived, John waited. John waited?", True],
  ["Until Sara arrived, John waited. Did John leave before Sara arrived?", None],

  # temporal clauses with anaphora

  ["After John bought a car, he washed it. John bought a car?", True],
  ["After John bought a car, he washed it. John washed the car?", True],
  ["After John bought a car, he washed it. Did John sell the car?", None],
  ["Before Mary wrote a letter, she found a pen. Mary found a pen?", True],
  ["Before Mary wrote a letter, she found a pen. Did Mary find a pencil?", None],
  ["Before Mary wrote a letter, she wrote a letter?", True],

  # PP attachment and structural scope

  ["John saw the man with a telescope. John saw the man?", True],
  ["John saw the man with a telescope. The man had a telescope?", None],
  ["John saw the bird in the garden. John saw the bird?", True],
  ["John saw the bird in the garden. The bird was in the garden?", True],
  ["John saw the bird in the garden. Did John see a fish in the garden?", None],
  ["Mary found the key under the table. Mary found the key?", True],
  ["Mary found the key under the table. The key was under the table?", True],
  ["Mary found the key under the table. Was the key on the table?", False],
  ["Tom put the book on the chair. The book was on the chair?", True],
  ["Tom put the book on the chair. Was the book on the floor?", None],
  ["Eve kept the milk in the fridge. The milk was in the fridge?", True],
  ["Eve kept the milk in the fridge. Was the milk on the counter?", None],
  ["John met the girl from Paris. John met the girl?", True],
  ["John met the girl from Paris. The girl was from Paris?", True],
  ["John met the girl from Paris. Was the girl from London?", None],
  ["Mary called the boy in the kitchen. Mary called the boy?", True],
  ["Mary called the boy in the kitchen. The boy was in the kitchen?", True],
  ["Mary called the boy in the kitchen. Was the boy in the garden?", None],

  # noun compounds and semi-compounds

  ["A school bus arrived. A bus arrived?", True],
  ["A school bus arrived. A truck arrived?", None],
  ["A chocolate cake fell. A cake fell?", True],
  ["A chocolate cake fell. A pie fell?", None],
  ["A stone wall collapsed. A wall collapsed?", True],
  ["A stone wall collapsed. A wall did not collapse?", False],
  ["A kitchen door was open. A door was open?", True],
  ["A village road was narrow. A road was narrow?", True],
  ["A village road was narrow. A road was wide?", False],
  ["A coffee cup broke. A cup broke?", True],
  ["A coffee cup broke. A plate broke?", None],
  ["A toy car rolled. A car rolled?", True],
  ["A garden wall was high. A wall was high?", True],
  ["A garden wall was high. A wall was low?", None],

  # reflexives and reciprocals

  ["John saw himself in the mirror. John saw John?", True],
  ["John saw himself in the mirror. Did John see Mary?", None],
  ["Mary blamed herself. Mary blamed Mary?", True],
  ["Tom washed himself. Tom washed Tom?", True],
  ["Tom washed himself. Did Tom wash Mary?", None],
  ["Eve introduced herself. Eve introduced Eve?", True],
  ["John and Mary saw each other. John saw Mary?", True],
  ["John and Mary saw each other. Mary saw John?", True],
  ["John and Mary saw each other. Did John see Eve?", None],
  ["Tom and Eve greeted each other. Tom greeted Eve?", True],
  ["Tom and Eve greeted each other. Eve greeted Tom?", True],
  ["Tom and Eve greeted each other. Did Tom greet Mary?", None],
  ["The boys helped themselves. The boys helped the boys?", True],
  ["The girls admired themselves. The girls admired the girls?", True],

  # coordination and modifier-scope edge cases

  ["A tall and quiet man entered. A man entered?", True],
  ["A tall and quiet man entered. A woman entered?", None],
  ["A tall and quiet man entered. The man was tall?", True],
  ["A tall and quiet man entered. The man was quiet?", True],
  ["A tall and quiet man entered. The man was short?", False],
  ["A red and blue flag waved. The flag was red?", True],
  ["A red and blue flag waved. The flag was blue?", True],
  ["A red and blue flag waved. The flag was green?", None],
  ["John bought a red car and a blue bicycle. John bought a car?", True],
  ["John bought a red car and a blue bicycle. John bought a bicycle?", True],
  ["John bought a red car and a blue bicycle. Did John buy a truck?", None],
  ["John bought a red car and a blue bicycle. The car was red?", True],
  ["John bought a red car and a blue bicycle. The bicycle was blue?", True],
  ["John bought a red car and a blue bicycle. The car was blue?", False],
  ["Mary washed and dried the cup. Mary washed the cup?", True],
  ["Mary washed and dried the cup. Mary dried the cup?", True],
  ["Mary washed and dried the cup. Did Mary break the cup?", None],
  ["Tom opened the door and the window. Tom opened the door?", True],
  ["Tom opened the door and the window. Tom opened the window?", True],
  ["Tom opened the door and the window. Tom did not open the door?", False],

  # coordinated relatives and stacked modifiers

  ["The man who laughed and who waved left. The man laughed?", True],
  ["The man who laughed and who waved left. The man waved?", True],
  ["The man who laughed and who waved left. Did the man cry?", None],
  ["The woman who sang and danced smiled. The woman sang?", True],
  ["The woman who sang and danced smiled. The woman danced?", True],
  ["The woman who sang and danced smiled. The woman did not sing?", False],
  ["The boy with a red hat and a blue coat ran. The boy had a red hat?", True],
  ["The boy with a red hat and a blue coat ran. The boy had a blue coat?", True],
  ["The boy with a red hat and a blue coat ran. Did the boy have a green hat?", None],

  # clause-complement but not knowledge/belief focused

  ["John said that Mary left. Mary left?", True],
  ["John said that Mary left. Did Mary stay?", None],
  ["Eve reported that Tom arrived. Tom arrived?", True],
  ["Eve reported that Tom arrived. Did Tom depart?", None],
  ["Anna announced that the show started. The show started?", True],
  ["Anna announced that the show started. The show did not start?", False],
  ["The guide explained that the road was closed. The road was closed?", True],
  ["The guide explained that the road was closed. Was the road open?", False],

  # light support for infinitival purpose clauses

  ["John went to the shop to buy bread. John went to the shop?", True],
  ["John went to the shop to buy bread. John bought bread?", None],
  ["John went to the shop to buy bread. Did John go to the bank?", None],
  ["Mary opened the window to let in air. Mary opened the window?", True],
  ["Mary opened the window to let in air. Mary did not open the window?", False],
  ["Mary opened the window to let in air. Air came in?", None],

  # concessive and contrastive subordinate clauses

  ["Although John was tired, he finished the work. John was tired?", True],
  ["Although John was tired, he finished the work. John finished the work?", True],
  ["Although John was tired, he finished the work. John did not finish the work?", False],
  ["Although John was tired, he finished the work. Was the work difficult?", None],
  ["Though Mary was ill, she traveled. Mary was ill?", True],
  ["Though Mary was ill, she traveled. Mary traveled?", True],
  ["Though Mary was ill, she traveled. Mary did not travel?", False],
  ["Though Mary was ill, she traveled. Did Mary recover?", None],

  # sentence adverbials and parenthetical-like material

  ["Fortunately, John found the key. John found the key?", True],
  ["Fortunately, John found the key. John did not find the key?", False],
  ["Fortunately, John found the key. Did John find the lock?", None],
  ["Sadly, Mary lost the letter. Mary lost the letter?", True],
  ["Sadly, Mary lost the letter. Did Mary find the letter?", None],
  ["Unexpectedly, the door opened. The door opened?", True],
  ["Unexpectedly, the door opened. The door did not open?", False],
  ["Apparently, Tom left early. Tom left early?", True],
  ["Apparently, Tom left early. Did Tom leave late?", None],

  # additional mixed constructions

  ["The doctor who treated Mary called John. The doctor treated Mary?", True],
  ["The doctor who treated Mary called John. The doctor called John?", True],
  ["The doctor who treated Mary called John. Did the doctor treat John?", None],
  ["The painter who lived in Rome sold a picture. The painter lived in Rome?", True],
  ["The painter who lived in Rome sold a picture. The painter sold a picture?", True],
  ["The painter who lived in Rome sold a picture. Did the painter live in Paris?", None],
  ["The student carrying the books greeted the teacher. The student carried the books?", True],
  ["The student carrying the books greeted the teacher. The student greeted the teacher?", True],
  ["The student carrying the books greeted the teacher. Did the student greet the principal?", None],
  ["The bicycle repaired by Mike was expensive. Mike repaired the bicycle?", True],
  ["The bicycle repaired by Mike was expensive. The bicycle was expensive?", True],
  ["The bicycle repaired by Mike was expensive. The bicycle was cheap?", False],
  ["John's friend from Paris bought a camera. John had a friend?", True],
  ["John's friend from Paris bought a camera. The friend was from Paris?", True],
  ["John's friend from Paris bought a camera. Was the friend from London?", None],
  ["Mary's brother carrying a box entered. Mary had a brother?", True],
  ["Mary's brother carrying a box entered. The brother carried a box?", True],
  ["Mary's brother carrying a box entered. Did the brother carry a bag?", None],

]
