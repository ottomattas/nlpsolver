[
  // == 1. BASIC TAXONOMY ==
  [["-isa", "thing", "?:Y"], ["isa", "object", "?:Y"]],
  [["-isa", "object", "?:Y"], ["isa", "thing", "?:Y"]],

  // == 2. PART-WHOLE & POSSESSION  ==
  // If Y1 is a subtype of Y2, and Y1 has part X, then Y2 has part X
  [
    ["-isa", "?:Y1", "?:Y2"], 
    ["-has part", "?:Y1", "?:X", "?:Ctxt"], 
    ["has part", "?:Y2", "?:X", "?:Ctxt"]
  ],
  // "Has part" implies "Have" (possession) [cite: 127, 345]
  [
    ["-has part", "?:Y", "?:X", "?:Ctxt"], 
    ["have", "?:Y", "?:X", "?:Ctxt"]
  ],
  // Transitivity of Part-Whole
  [
    ["-has part", "?:A", "?:B", "?:Ctxt"],
    ["-has part", "?:B", "?:C", "?:Ctxt"],
    ["has part", "?:A", "?:C", "?:Ctxt"]
  ],
  
  /*
  // == X. INSIDE, OUTSIDE etc  ==
  [ 
    ["-has degree rel2","in","?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"], 
    ["-has degree rel2","in","?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"],  
    ["-has degree rel2","in","?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"]
  ],
  
  [ 
    ["-has degree rel2","in","?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"], 
    ["-has degree rel2","in","?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"],  
    ["-has degree rel2","in","?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"]
  ],
  */

  // == 3. GRADABLE RELATIONS (TRANSITIVITY & LOGIC) ==
  // Transitivity for TRUE comparative relations only (degree=high/more/less).
  // Intentionally excludes degree="none" (binary relations like "afraid of")
  // to avoid spurious transitive chains. [cite: 350, 357]
  [
    ["-has degree rel2", "?:R", "?:X", "?:Y", "high", "?:Rel", "?:Ctxt"],
    ["-has degree rel2", "?:R", "?:Y", "?:Z", "high", "?:Rel", "?:Ctxt"],
    ["has degree rel2", "?:R", "?:X", "?:Z", "high", "?:Rel", "?:Ctxt"]
  ],
  [
    ["-has degree rel2", "?:R", "?:X", "?:Y", "more", "?:Rel", "?:Ctxt"],
    ["-has degree rel2", "?:R", "?:Y", "?:Z", "more", "?:Rel", "?:Ctxt"],
    ["has degree rel2", "?:R", "?:X", "?:Z", "more", "?:Rel", "?:Ctxt"]
  ],
  [
    ["-has degree rel2", "?:R", "?:X", "?:Y", "less", "?:Rel", "?:Ctxt"],
    ["-has degree rel2", "?:R", "?:Y", "?:Z", "less", "?:Rel", "?:Ctxt"],
    ["has degree rel2", "?:R", "?:X", "?:Z", "less", "?:Rel", "?:Ctxt"]
  ],
  // Comparative to Property Bridge: If X is taller than Y, then X is tall [cite: 345, 355]
  [
    ["-has degree rel2", "?:R", "?:X", "?:Y", "?:Deg", "?:Rel", "?:Ctxt"],
    ["has degree property", "?:R", "?:X", "none", "?:Rel", "?:Ctxt"]
  ],

  // == 4. SPATIAL & CATEGORICAL TRANSITIVITY ==
  // Transitivity for non-gradable "is rel2" relations [cite: 352, 353]
  [["-is rel2", "in", "?:X", "?:Y", "?:Ctxt"], ["-is rel2", "in", "?:Y", "?:Z", "?:Ctxt"], ["is rel2", "in", "?:X", "?:Z", "?:Ctxt"]],
  //[["-is rel2", "on", "?:X", "?:Y", "?:Ctxt"], ["-is rel2", "on", "?:Y", "?:Z", "?:Ctxt"], ["is rel2", "on", "?:X", "?:Z", "?:Ctxt"]],
  [["-is rel2", "inside", "?:X", "?:Y", "?:Ctxt"], ["-is rel2", "inside", "?:Y", "?:Z", "?:Ctxt"], ["is rel2", "inside", "?:X", "?:Z", "?:Ctxt"]],
  [["-is rel2", "located in", "?:X", "?:Y", "?:Ctxt"], ["-is rel2", "located in", "?:Y", "?:Z", "?:Ctxt"], ["is rel2", "located in", "?:X", "?:Z", "?:Ctxt"]],
  [["-is rel2", "connected to", "?:X", "?:Y", "?:Ctxt"], ["-is rel2", "connected to", "?:Y", "?:Z", "?:Ctxt"], ["is rel2", "connected to", "?:X", "?:Z", "?:Ctxt"]],
  [["-is rel2", "part of", "?:X", "?:Y", "?:Ctxt"], ["-is rel2", "part of", "?:Y", "?:Z", "?:Ctxt"], ["is rel2", "part of", "?:X", "?:Z", "?:Ctxt"]],
  // "contains" is the converse of "in": A contains B ↔ B is in A
  [["-is rel2", "contains", "?:A", "?:B", "?:Ctxt"], ["is rel2", "in", "?:B", "?:A", "?:Ctxt"]],
  [["-is rel2", "in", "?:B", "?:A", "?:Ctxt"], ["is rel2", "contains", "?:A", "?:B", "?:Ctxt"]],
  
  // AND/OR add a synonym bridge:
  [["-is rel2", "on", "?:X", "?:Y", "?:Ctxt"], ["is rel2", "in", "?:X", "?:Y", "?:Ctxt"]],

  // == 5. ACTIVITY & MOVEMENT (BAbI TASK LOGIC) ==
  // Davidsonian Activity Reification: activity + has type + has actor [cite: 334, 335, 354]
  [
    ["-typical", "?:E", "?:Ctxt"],
    ["-has type", "?:E", "?:V", "?:Ctxt"],
    ["-has actor", "?:E", "?:X", "?:Ctxt"],
    ["typically", "?:X", "?:V", "?:Ctxt"]
  ],
  // Capability: If one typically does V, one can do V [cite: 354]
  [["-typically", "?:X", "?:V", "?:Ctxt"], ["can", "?:X", "?:V", "?:Ctxt"]],
  // Movement Results: If X 'go'es to Dest, X is 'at' Dest in the next state [cite: 146, 147]
  [
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
    ["-has type", "?:E", "go", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
    ["-has destination", "?:E", "?:Dest", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
    ["is rel2", "at", "?:X", "?:Dest", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]
  ],
  // Movement also works with has_direction (synonym for has_destination in some parses)
  [
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
    ["-has type", "?:E", "go", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
    ["-has direction", "?:E", "?:Dest", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
    ["is rel2", "at", "?:X", "?:Dest", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]
  ],
  // Movement Synonyms
  [["-has type", "?:E", "travel", "?:Ctxt"], ["has type", "?:E", "go", "?:Ctxt"]],
  [["-has type", "?:E", "journey", "?:Ctxt"], ["has type", "?:E", "go", "?:Ctxt"]],
  [["-has type", "?:E", "move", "?:Ctxt"], ["has type", "?:E", "go", "?:Ctxt"]],

  // == 6. PERSISTENCE (FRAME PROBLEM) ==
  // Default persistence of relations from W0 to W1 unless blocked [cite: 36, 148, 166]
  {
    "@confidence": 0.99,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // Persistence of "have" (possession) from W0 to W1 [cite: 36, 148]
  {
    "@confidence": 0.99,
    "@logic": [
      ["-have", "?:Y", "?:X", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },

  // == 7. SETS & COUNTING ==
  // Subset Cardinality: |A ∩ B| <= |A| [cite: 355]
  [
    ["=", "?:N", ["$count", ["$setof", ["and", "?:X1", "?:X2"], "?:Y1"]]],
    ["=>", ["$greatereq", ["$count", ["$setof", "?:X1", "?:Y1"]], "?:N"]]
  ],
  // Two-condition set cardinality
  [
    ["=", "?:N", ["$count", ["$setof", ["and", "?:X1", "?:X2", "?:X3"], "?:Y1"]]],
    ["=>", ["$greatereq", ["$count", ["$setof", ["and", "?:X1", "?:X2"], "?:Y1"]], "?:N"]]
  ],
  // Three-condition set cardinality
  [
    ["=", "?:N", ["$count", ["$setof", ["and", "?:X1", "?:X2", "?:X3", "?:X4"], "?:Y1"]]],
    ["=>", ["$greatereq", ["$count", ["$setof", ["and", "?:X1", "?:X2", "?:X3"], "?:Y1"]], "?:N"]]
  ],
  // Set Type Constraint
  [["-member", "?:X", "?:S", "?:Ctxt"], ["-is set of", "?:Type", "?:S", "?:Ctxt"], ["isa", "?:Type", "?:X"]],

  // == 8. MEASUREMENTS & ATTRIBUTES ==
  // Value Holders [cite: 306, 307]
  [["isa", "weight", ["$theof1", "weight", "?:O", "?:Ctxt"]]],
  [["isa", "price", ["$theof1", "price", "?:O", "?:Ctxt"]]],
  [["isa", "length", ["$theof1", "length", "?:O", "?:Ctxt"]]],
  // Property to Attribute Mapping
  [
    ["-has degree property", "red", "?:X", "none", "?:Rel", "?:Ctxt"],
    ["is rel2", "color of", "red", "?:X", "?:Ctxt"]
  ]
]
