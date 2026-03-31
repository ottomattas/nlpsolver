[

// from conceptnet:

{"@role": "axiom", "@confidence": 1.0, "@logic": [["be", "wing", "?:X1"], "=>", ["usedfor", "fly", "?:X1"] ]},

// from quasimodo with an additional blocker sub-priority 20:

{"@role": "axiom", "@confidence": 0.998553831433605, "@logic": [["be", "bird", "?:X1"], "=>", [["hasa", "wing", "?:X1"], "|", ["$block", ["$","bird",20], ["$not", ["hasa", "wing", "?:X1"]]]]]},

// from quasimodo with an additional blocker sub-priority 10:

{"@role": "axiom", "@confidence": 0.9927050249461986, "@logic": [["be", "bird", "?:X1"], "=>", [["capability", "fly", "?:X1"], "|", ["$block", ["$","bird",10], ["$not", ["capability", "fly", "?:X1"]]]]]},

// our commonsense rule:

{"@role": "assumption", "@confidence": 1.0, "@logic": [["-hasa", "?:O", "?:C"], ["-usedfor", "?:U", "?:O"], ["-be","?:C","?:I"], ["hasa", "?:O", "?:I"], ["-capability","?:U","?:I"]] },

// reflexivity of be:

{"@role": "assumption","@confidence": 1.0, "@logic": ["be", "?:P", "?:P"]},

// question assumptions:

{"@role": "assumption", "@confidence": 1.0, "@logic":  ["be","bird","any_bird_constant"]},

["-hasa", "wing", "any_bird_constant"], 

// question:

{"@question": ["-capability","fly","any_bird_constant"]}

]

