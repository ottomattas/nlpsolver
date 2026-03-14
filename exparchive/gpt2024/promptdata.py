
[
["John is a person", None, ["isa","person","John"]],
["There was a car.", None, ["exists","X", ["isa","car","X"]]],
["A bear is an animal", None, ["forall","X", ["implies",["isa","bear","X"], ["isa","X","animal"]]]],

["All green things are rough", None, ["forall","X", ["implies",["and",["has property","X","green"], ["isa","thing","X"]],["has property","X","rough"]]]],
["Some animals are small", None,   ["exists","X",["and",["isa","animal","X"], ["has property","X","small"]]]], 
["Dinosaurs were heavy animals", None,   ["forall","X", ["implies",["isa","dinosaur","X"], ["has property","X","heavy"]]]], 

["Dogs have paws", None,  ["forall","X", ["implies",["isa","dog","X"], ["exists","Y",["and",["isa","paws","Y"],["have","X","Y"]]]]]],
["Dogs had paws", None,  ["exists","X", ["and",["isa","dogs","X"], ["exists","Y",["and",["isa","paws","Y"],["had","X","Y"]]]]]],
["A car has wheels", None,   ["forall","X", ["implies",["isa","car","X"], ["exists","Y",["and",["isa","wheels","Y"],["has","X","Y"]]]]]],
["Bears have a tail", None, ["forall","X", ["implies",["isa","bear","X"], ["exists","Y",["and",["isa","tail","Y"],["have","X","Y"]]]]]],
["Bears had a tail", None, ["exists","X", ["and",["isa","bears","X"],["exists","Y",["and",["isa","tail","Y"],["had","X","Y"]]]]]],
["The bear had a berry", None, ["exists","X", ["and",["isa","bear","X"],["exists","Y",["and",["isa","Y","berry"],["had","X","Y"]]]]]],
["Dinosaurs had big heads", None,    ["forall","X", ["implies",["isa","dinosaur","X"], ["exists","Y",["and",["isa","head","Y"],["has property","Y","big"],["had","X","Y"]]]]]],
["Americans have a capital", None,  ["exists","Y", ["and",["isa","capital","Y"], ["forall","X", ["implies",["isa","american","X"], ["have","X","Y"]]]]]],
["Chinese had a capital", None, ["exists","Y", ["and",["isa","capital","Y"], ["forall","X", ["implies",["isa","chinese","X"], ["had","X","Y"]]]]]],
["The dog had a bone", None,   ["exists","X", ["and",["isa","dog","X"],["exists","Y",["and",["isa","bone","Y"],["had","X","Y"]]]]]],

["Pete is not a man", None, ["not",["isa","Pete","man"]]],
["Pete is not a bad man", None, ["not",["and",["has property","Pete","bad"],["isa","man","Pete"]]]],
["John does not have a car", None, ["not",["exists","X", ["and",["isa","car","X"],["have","John","X"]]]]],
["White objects are not black", None, ["forall","X", ["implies",["and",["has property","X","white"], ["isa","object","X"]],["not",["has property","X","black"]]]]],
["Elephants have no wings", None, ["forall","X", ["implies",["isa","elephant","X"],["not",["exists","Z",["and",["isa","wing","Z"],["have","X","Z"]]]]]]],

["John has a car or a bike", None, ["xor",["exists","X", ["and",["isa","car","X"],["has","John","X"]]],["exists","Y", ["and",["isa","bike","Y"],["has","John","Y"]]]]],
["Alice is either good or bad", None, ["xor", ["has property","good","Alice"], ["has property","bad","Alice"]]],
["John or Mary has a car", None, ["or",["exists","X", ["and",["isa","car","X"],["has","John","X"]]],["exists","Y", ["and",["isa","car","Y"],["has","Mary","Y"]]]]],

["John is a brother of Mike", None, ["rel2","brother","John","Mike"]],
["Obama was a president of USA", None,  ["rel2","president","USA https://en.wikipedia.org/wiki/United_States","Obama https://en.wikipedia.org/wiki/Barack_Obama"]],
["USA's president was Obama", None,  ["rel2","president","USA https://en.wikipedia.org/wiki/United_States","Obama https://en.wikipedia.org/wiki/Barack_Obama"]],
["Tallinn is north of Riga", None, ["rel2","north","Tallinn https://en.wikipedia.org/wiki/Tallinn","Riga https://en.wikipedia.org/wiki/Riga"]],
["Tallinn is near Riga", None, ["rel2","near","Tallinn https://en.wikipedia.org/wiki/Tallinn","Riga https://en.wikipedia.org/wiki/Riga"]],
["Point A is connected to point B.", None, ["rel2","connected","A","B"]],
["Tallinn is on the seacoast", None, ["exists","X",["and",["isa","seacoast","X"],["rel2","on","Tallinn https://en.wikipedia.org/wiki/Tallinn","X"]]]],
["John and Mike are in a small room", None, ["exists","X",["and",["isa","room","X"],["has property","X","small"],["rel2","in","John","X"],["rel2","in","Mike","X"]]]],
["Ceilings are above doors", None, ["forall","X",["forall","Y",["implies",["and",["isa","ceiling","X"],["isa","door","Y"]],["rel2","above","X","Y"]]]]],
["Dole was defeated by Clinton", None, ["rel2","defeated","Clinton https://en.wikipedia.org/wiki/Bill_Clinton","Dole https://en.wikipedia.org/wiki/Bob_Dole"]],
["John defeated Mike", None, ["rel2","defeated","John","Mike"]],

["John is stronger than Mike", None, [">",["$value",["property of","John","strength"]], ["$value", ["property of", "Mike", "strength"]]]],
["Eve is as nice as Mike", None, ["=",["$value",["property of","Eve","nice"]], ["$value", ["property of", "Mike", "nice"]]]],

["Michael likes Eve", None, ["has attitude","like","Michael","Eve"]],
["Bears like honey", None, ["forall","X", ["implies",["isa","bear","X"], ["forall","Y",["implies",["isa","Y","honey"],["has attitude","like","X","Y"]]]]]],
["Bears liked cakes", None, ["exists","X", ["and",["isa","bears","X"],["exists","Y",["and",["isa","Y","cake"],["had attitude","like","X","Y"]]]]]],
["Dogs like meat", None,  ["forall","X", ["implies",["isa","dog","X"], ["forall","Y",["implies",["isa","Y","meat"],["has attitude","like","X","Y"]]]]]],
["The dog liked berries", None,  ["exists","X", ["and",["isa","dog","X"],["exists","Y",["and",["isa","Y","berry"],["had attitude","like","X","Y"]]]]]],
["The dog wanted meat", None,  ["exists","X", ["and",["isa","dog","X"],["forall","Y",["implies",["isa","Y","meat"],["had attitude","want","X","Y"]]]]]],
["The bear likes berries", None, ["exists","X", ["and",["isa","bear","X"],["forall","Y",["implies",["isa","Y","berry"],["has attitude","like","X","Y"]]]]]],
["John does not like cakes", None, ["forall","Y",["implies",["isa","Y","cake"],["not",["has attitude","like","John","Y"]]]]],

["Mike notices Eve", None, ["exists","A",["and",["isa","activity","A"],["has type","A","notice"],["has time","A","present"],["has actor","A","John"],["has target","A","Eve"]]]],
["John ran quickly", None, ["exists","A",["and",["isa","activity","A"],["has type","A","run"],["has time","A","past"],["has manner","A","quickly"],["has actor","A","John"]]]],
["John ate a sandwich", None, ["exists","A",["exists","Y",["and",["isa","activity","A"],["isa","sandwitch","Y"],["has type","A","eat"],["has time","A","past"],["has actor","A","John"],["has target","A","Y"]]]]],
["The bear ate berries", None,  ["exists","X", ["and",["isa","bear","X"],["exists","Y",["and",["isa","Y","berries"],["exists","A",["and",["isa","activity","A"],["has type","A","eat"],["has time","A","past"],["has actor","A","X"],["has target","A","Y"]]]]]]]],
["Titanic sank in the Atlantic", None, ["exists","A",["and",["isa","activity","A"],["has type","A","sink"],["has time","A","past"],["has location","A","Atlantic https://en.wikipedia.org/wiki/Atlantic_Ocean"],["has actor","A","Titanic https://en.wikipedia.org/wiki/RMS_Titanic"]]]],

["A big dog likes to bark", None, ["exists","X", ["and",["isa","dog","X"],["has property","X","big"],["forall","A",["implies",["and",["isa","activity","A"],["has type","A","bark"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]],
["A dog likes to howl", None,  ["forall","X", ["implies",["isa","dog","X"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","howl"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]],
["A big dog ate a carrot", None,   ["exists","X", ["and",["isa","dog","X"],["has property","X","big"],["exists","Y",["and",["isa","carrot","Y"],["exists","A",["and",["isa","activity","A"],["has type","A","eat"],["has time","A","past"],["has actor","A","X"],["has target","A","Y"]]]]]]]],
["The dog ate bones", None,  ["exists","X",["and",["isa","dog","X"],["exists","Y",["and",["isa","bones","Y"],["exists","A",["and",["isa","activity","A"],["has type","A","eat"],["has time","A","past"],["has actor","A","X"],["has target","A","Y"]]]]]]]],
["A red bear likes to sleep", None,  ["exists","X", ["and",["isa","bear","X"], ["has property","X","red"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]],
["A bear likes to sleep", None,  ["forall","X", ["implies",["isa","bear","X"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["has attitude","like","X","A"]]]]]   ],
["A bear liked to sleep", None,  ["exists","X", ["implies",["isa","bear","X"], ["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["had attitude","like","X","A"]]]]]],
["Bears liked to sleep", None, ["exists","X", ["and",["isa","bears","X"],["forall","A",["implies",["and",["isa","activity","A"],["has type","A","sleep"],["has actor","A","X"]],["had attitude","like","X","A"]]]]]],

["John was a teacher at a school", None,   ["exists","Y", ["and",["isa","school","Y"], ["exists","X",["isa","job","X"], ["had","John","X"],["has location","X","Y"],["has type","X","teacher"]]]]],
["A man lives in a red house", None,  ["exists","X", ["and",["isa","man","X"],["exists","Y",["and",["isa","house","Y"],["has property","Y","red"], ["exists","Z",["isa","activity","Z"],["has type","Z","live"],["has location","Z","Y"],["has time","Z","present"],["has actor","Z","X"]]]]]]],
["Teachers work at a school", None,  ["forall","X", ["implies",["isa","teacher","X"], ["exists","Y",["and",["isa","school","Y"],["exists","Z",["isa","activity","Z"],["has type","Z","work"],["has location","Z","Y"],["has actor","Z","X"]]]]]]],
["John goes to New York for fun", None,  ["exists","Z",["isa","activity","Z"],["has type","Z","go"],["has target","Z","New York https://en.wikipedia.org/wiki/New_York_City"],["has goal","Z","fun"],["has actor","Z","John"]]],

["John walked in Mary's house", None, ["exists","A",["and",["isa","activity","A"],["has type","A","walk"],["has time","A","past"],["has actor","A","John"],["exists","X",["and",["isa","house","X"],["have","Mary","X"],["rel2","in","A","X"]]]]]],

["Birds can fly", None, ["forall","X", ["implies",["isa","bird","X"], ["and",["exists","Y",["and",["isa","activity","Y"],["has type","Y","flying"],["has actor","Y","X"]]],["is able","X","Y"]]]]],
["Birds fly", None, ["forall","X", ["implies",["isa","bird","X"], ["and",["exists","Y",["and",["isa","activity","Y"],["has type","Y","flying"],["has actor","Y","X"]]],["typical activity","X","Y"]]]]],
["Dogs bark", None, ["forall","X", ["implies",["isa","dog","X"], ["and",["exists","Y",["and",["isa","activity","Y"],["has type","Y","barking"],["has actor","Y","X"]]],["typical activity","X","Y"]]]]],
["Penguins cannot fly", None, ["forall","X", ["implies",["isa","bird","X"], ["forall","Y",["implies",["and",["isa","activity","Y"],["has type","Y","flying"],["has actor","Y","X"]],["not",["is able","X","Y"]]]]]]],

["John has five apples", None, ["exists","X",["and",["is set of","apple","X"],["=",5,["$count","X"]],["has","John","X"],["forall","Y",["implies",["and",["isa","apple","Y"],["has","John","Y"]],["member","Y","X"]]]]]],
["John has several apples", None, ["exists","X",["and",["is set of","apple","X"],[">",["$count","X"],1],["has","John","X"]]]],
["John has two red and three green apples", None, ["and",["exists","X",["and",["is set of",["and",["isa","apple","X"],["has property","X","red"]]],["=",["$count","X"],2],["has","John","X"]]],["exists","Y",["and",["is set of",["and",["isa","apple","Y"],["has property","Y","green"]]],["=",["$count","X"],3],["has","John","Y"]]]]],

["The length of Emajogi is 80 kilometers", None, ["and",["has property","Emajogi https://en.wikipedia.org/wiki/Emaj%C3%B5gi",["$measure1","length","Emajogi","kilometer"]],["=",80,["$value",["$measure1","length","Emajogi","kilometer"]]]]],
["The price of the red car is 2 dollars", None, ["exists","X",["and",["isa","car","X"],["has property","X","red"],["=",2,["$value",["$measure1","price","X","dollar"]]]]]],
["Bikes are lighter than cars", None, ["forall","X",["forall","Y",["implies",["and",["isa","bike","X"],["isa","car","Y"]],["<",["$value",["$measure1","weight","X","kilograms"]],["$value",["$measure1","weight","Y","kilograms"]]]]]]],

["John is nice. Eve is a woman. He has a car.", None, ["and",["has property","John","nice"],["isa","woman","Eve"],["exists","X",["isa","car","X"],["has","John","X"]]]],
["The bear is big. The animal is thirsty.", None, ["exists","X",["and",["isa","bear","X"],["has property","X","big"],["has property","X","thirsty"]]]],
["The cup is small. The engine is strong.", None, ["and",["exists","X",["and",["isa","cup","X"],["has property","X","small"]]],["exists","Y",["isa","engine","Y"],["has property","Y","strong"]]]],

["Is John strong?", None, ["question",["has property","John","strong"]]],
["Five is not smaller than three?", None, ["question",["not",["<",5,3]]]],
["Who likes Mike?", None, ["ask","Y",["has attitude","like","Mike","Y"]]],
["Which man is big?", None, ["ask","X",["and",["isa","man","X"],["has property","X","big"]]]],
["Where did John go?", None, ["ask","Y",["exists","X",["and",["isa","activity","X"],["has type","X","go"],["has actor","X","John"],["has target","X","Y"]]]]],
["Mike is an elephant. Mary is a cat. Who is an elephant?", None, ["and",["isa","elephant","Mike"],["isa","cat","Mary"], ["ask","X",["isa","elephant","X"]]]]
]


