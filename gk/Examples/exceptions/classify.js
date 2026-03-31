
[

// the task is to classify three objects: h1 (likely human), b1 (likely bird), a1 (likely airplane)
//
// the question at the end asks to find objects which are likely to be organisms, along with the
// confidence that they are organisms

// here we give observations about parts our three objects have

{"@logic": ["has_part","h1","leg"]},

{"@logic": ["has_part","b1","leg"]},
{"@logic": ["has_part","b1","wing"]},
{"@logic": ["has_part","b1","feathers"]},

{"@logic": ["has_part","a1","engine"]},
{"@logic": ["has_part","a1","wing"]},

// here we give default rules with confidences about classifying as humans, birds, airplanes
// the $block literal says that the application of this rule is not allowed, if the second argument of
// the $block predicate can be proved

// as an example, the first rule says that if something has a leg, then with the 30% confidence it is a human, unless we can prove
// that it is not a human

{"@logic": [["has_part","?:X","leg"],"=>",[["isa","?:X","human"],"|",["$block", ["$","human"], ["$not", ["isa","?:X","human"]]]]], "@confidence":30},
{"@logic": [["has_part","?:X","leg"],"=>",[["isa","?:X","bird"],"|",["$block", ["$","bird"], ["$not", ["isa","?:X","bird"]]]]], "@confidence":20},

{"@logic": [["has_part","?:X","wing"],"=>",[["isa","?:X","bird"],"|",["$block", ["$","bird"], ["$not", ["isa","?:X","bird"]]]]], "@confidence":60},
{"@logic": [["has_part","?:X","feathers"],"=>",[["isa","?:X","bird"],"|",["$block", ["$","bird"], ["$not", ["isa","?:X","bird"]]]]], "@confidence":80},

{"@logic": [["has_part","?:X","wing"],"=>",[["isa","?:X","airplane"],"|",["$block", ["$","airplane"], ["$not", ["isa","?:X","airplane"]]]]], "@confidence":40},

// a strict rule saying that if something has an engine as a part, then this thing is not an organism

{"@logic": [["has_part","?:X","engine"],"=>",["-isa","?:X","organism"]]},

// a taxonomy: humans and birds are organisms, airplanes are not organisms

{"@logic": [["isa","?:X","human"],"=>",["isa","?:X","organism"]]},
{"@logic": [["isa","?:X","bird"],"=>",["isa","?:X","organism"]]},
{"@logic": [["isa","?:X","airplane"],"=>",["-isa","?:X","organism"]]},

/*
{"@logic": [["isa","?:X","airplane"],"=>",["has_part","?:X","engine"]]},
{"@logic": [["isa","?:X","airplane"],"=>",["has_part","?:X","wing"]]},
{"@logic": [["isa","?:X","airplane"],"=>",["-has_part","?:X","feathers"]]},
{"@logic": [["isa","?:X","bird"],"=>",["has_part","?:X","wing"]]},
{"@logic": [["isa","?:X","bird"],"=>",["has_part","?:X","leg"]]},
{"@logic": [["isa","?:X","human"],"=>",["has_part","?:X","leg"]]},
*/

// a question to find objects which are organisms, along with the confidence:

{"@question": ["isa","?:X","organism"]}

]
