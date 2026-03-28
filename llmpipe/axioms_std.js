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
  
  // == 9. DEGREE INTENSITY AXIOMS ==

  // --- Property Intensity Bridges ---

  // If a property is high intensity, it satisfies the plain property (high -> none)
  [
    ["-has degree property", "?:W", "?:X", "high", "?:RC", "?:Ctxt"],
    ["has degree property", "?:W", "?:X", "none", "?:RC", "?:Ctxt"]
  ],

  // If a property is low intensity, it satisfies the plain property (low -> none)
  [
    ["-has degree property", "?:W", "?:X", "low", "?:RC", "?:Ctxt"],
    ["has degree property", "?:W", "?:X", "none", "?:RC", "?:Ctxt"]
  ],

  // A property cannot be both high and low intensity (Contradiction)
  [
    ["-has degree property", "?:W", "?:X", "high", "?:RC", "?:Ctxt"],
    ["-has degree property", "?:W", "?:X", "low", "?:RC", "?:Ctxt"]
  ],

  // --- Relation Intensity Bridges ---

  // If a relation is high intensity, it satisfies the plain relation (high -> none)
  [
    ["-has degree rel2", "?:W", "?:X", "?:Y", "high", "?:RC", "?:Ctxt"],
    ["has degree rel2", "?:W", "?:X", "?:Y", "none", "?:RC", "?:Ctxt"]
  ],

  // If a relation is low intensity, it satisfies the plain relation (low -> none)
  [
    ["-has degree rel2", "?:W", "?:X", "?:Y", "low", "?:RC", "?:Ctxt"],
    ["has degree rel2", "?:W", "?:X", "?:Y", "none", "?:RC", "?:Ctxt"]
  ],

  // A relation cannot be both high and low intensity (Contradiction)
  [
    ["-has degree rel2", "?:W", "?:X", "?:Y", "high", "?:RC", "?:Ctxt"],
    ["-has degree rel2", "?:W", "?:X", "?:Y", "low", "?:RC", "?:Ctxt"]
  ],

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
  
  // event -> "is rel2" bridge for "like"
  /*
  [
    ["isa","activity","?:E"],
    ["-has type", "?:E", "like", "?:Ctxt"],
    ["-has actor", "?:E", "?:X", "?:Ctxt"],
    ["-has target", "?:E", "?:Y", "?:Ctxt"],
    ["is rel2", "like", "?:X", "?:Y", "?:Ctxt"]
  ],
  */
   [
    ["-isa","activity","?:E"],
    ["-has type", "?:E", "like", ["$ctxt","?:T1","?:W","?:Fv3","?:Fv4"]],
    ["-has actor", "?:E", "?:X", ["$ctxt","?:T1","?:W","?:Fv3","?:Fv4"]],
    ["-has target", "?:E", "?:Y", ["$ctxt","?:T1","?:W","?:Fv3","?:Fv4"]],
    ["-has time", "?:E", "?:T2", "?:Prep_t", ["$ctxt","?:T3","?:W","?:Fv3","?:Fv4"]],
    ["is rel2", "like", "?:X", "?:Y", ["$ctxt","?:T2","?:W","?:Fv3","?:Fv4"]]
  ],

  /*  
  [
    ["isa","activity","?:E"],
    ["-has type", "?:E", "like", "?:Ctxt"],
    ["-has actor", "?:E", "?:X", "?:Ctxt"],
    ["-has target", "?:E", "?:Y", "?:Ctxt"],
    ["has degree rel2", "like", "?:X", "?:Y", "none", "?:Cl", "?:Ctxt"] 
  ],
  */
  
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
  
  // If E is typical and X is the actor, then X can E.
  [
    ["-typical", "?:E", "?:Ctxt"],
    ["-has actor", "?:E", "?:X", "?:Ctxt"],
    ["can", "?:X", "?:E", "?:Ctxt"]
  ],

  // Capability: If one typically does V, one can do V [cite: 354]
  [["-typically", "?:X", "?:V", "?:Ctxt"], ["can", "?:X", "?:V", "?:Ctxt"]],  

  [["-typically", "?:X", "?:V", ["$ctxt", "?:Time", "?:W", "?:Loc", "?:KB"]], 
   ["isa", "activity", ["sk_E", "?:X", "?:V", "?:Time", "?:W", "?:Loc", "?:KB"]]],

  [["-typically", "?:X", "?:V", ["$ctxt", "?:Time", "?:W", "?:Loc", "?:KB"]], 
   ["has type", ["sk_E", "?:X", "?:V", "?:Time", "?:W", "?:Loc", "?:KB"], "?:V"]],

  [["-typically", "?:X", "?:V", ["$ctxt", "?:Time", "?:W", "?:Loc", "?:KB"]], 
   ["has actor", ["sk_E", "?:X", "?:V", "?:Time", "?:W", "?:Loc", "?:KB"], "?:X"]],

  [["-typically", "?:X", "?:V", ["$ctxt", "?:Time", "?:W", "?:Loc", "?:KB"]], 
   ["has time", ["sk_E", "?:X", "?:V", "?:Time", "?:W", "?:Loc", "?:KB"], "?:Time", "?:Prep_t"]],

  [["-typically", "?:X", "?:V", ["$ctxt", "?:Time", "?:W", "?:Loc", "?:KB"]],
   ["has location", ["sk_E", "?:X", "?:V", "?:Time", "?:W", "?:Loc", "?:KB"], "?:Loc", "?:Prep_l"]],

  [["-typically", "?:X", "?:V", ["$ctxt", "?:Time", "?:W", "?:Loc", "?:KB"]], 
   ["typical", ["sk_E", "?:X", "?:V", "?:Time", "?:W", "?:Loc", "?:KB"]]],
   
   // == 8. ACTION MODAL BRIDGES ==

  // Axiom 1: Track-2 Habitual -> Capability (DEFEASIBLE)
  // "If E is a typical event for X, then X can E, unless blocked."
  [
    ["-typical", "?:E", "?:Ctxt"],
    ["-has actor", "?:E", "?:X", "?:Ctxt"],
    ["can", "?:X", "?:E", "?:Ctxt"],
    ["$block", ["bridge_typical", "?:E"], ["$not", ["can", "?:X", "?:E", "?:Ctxt"]]]
  ],

  // Axiom 2: Track-2 Event -> Capability (STRICT)
  // "If an event occurred, the actor must have been able to do it."
  [
    ["-isa", "activity", "?:E", "?:Ctxt"],
    ["-has actor", "?:E", "?:X", "?:Ctxt"],
    ["can", "?:X", "?:E", "?:Ctxt"]
  ],

  // Axiom 3: Track-1 Habitual -> Capability (DEFEASIBLE)
  // "If X typically does V, then X can do V, unless blocked."
  [
    ["-typically", "?:X", "?:V", "?:Ctxt"],
    ["can", "?:X", "?:V", "?:Ctxt"],
    ["$block", ["bridge_typically", "?:V"], ["$not", ["can", "?:X", "?:V", "?:Ctxt"]]]
  ],

  // Axiom 4: Davidsonian to Atomic Bridge (STRICT)
  // "If X can do specific event E of type V, then X can do V."
  [
    ["-can", "?:X", "?:E", "?:Ctxt"],
    ["-has type", "?:E", "?:V", "?:Ctxt"],
    ["can", "?:X", "?:V", "?:Ctxt"]
  ],
  

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
  // Default persistence of "is rel2" relations across world states
  // W0 -> W1
  {
    "@confidence": 0.99,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // W1 -> W2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W2", "?:L", "?:K"]]]]
    ]
  },
  // W2 -> W3
  {
    "@confidence": 0.99,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W3", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "W3", "?:L", "?:K"]]]]
    ]
  },

  // Default persistence of "have" (possession) across world states
  // W0 -> W1
  {
    "@confidence": 0.99,
    "@logic": [
      ["-have", "?:Y", "?:X", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // W1 -> W2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-have", "?:Y", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W2", "?:L", "?:K"]]]]
    ]
  },
  // W2 -> W3
  {
    "@confidence": 0.99,
    "@logic": [
      ["-have", "?:Y", "?:X", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W3", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["have", "?:Y", "?:X", ["$ctxt", "?:T", "W3", "?:L", "?:K"]]]]
    ]
  },

  // Default persistence of "has property" across world states
  // W0 -> W1
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has property", "?:P", "?:X", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["has property", "?:P", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has property", "?:P", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // W1 -> W2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has property", "?:P", "?:X", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["has property", "?:P", "?:X", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has property", "?:P", "?:X", ["$ctxt", "?:T", "W2", "?:L", "?:K"]]]]
    ]
  },
  // W2 -> W3
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has property", "?:P", "?:X", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["has property", "?:P", "?:X", ["$ctxt", "?:T", "W3", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has property", "?:P", "?:X", ["$ctxt", "?:T", "W3", "?:L", "?:K"]]]]
    ]
  },

  // Default persistence of "has degree property" across world states
  // W0 -> W1
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // W1 -> W2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W2", "?:L", "?:K"]]]]
    ]
  },
  // W2 -> W3
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W3", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "W3", "?:L", "?:K"]]]]
    ]
  },

  // Default persistence of "can" across world states
  // W0 -> W1
  {
    "@confidence": 0.99,
    "@logic": [
      ["-can", "?:X", "?:A", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["can", "?:X", "?:A", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["can", "?:X", "?:A", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // W1 -> W2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-can", "?:X", "?:A", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["can", "?:X", "?:A", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["can", "?:X", "?:A", ["$ctxt", "?:T", "W2", "?:L", "?:K"]]]]
    ]
  },
  // W2 -> W3
  {
    "@confidence": 0.99,
    "@logic": [
      ["-can", "?:X", "?:A", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["can", "?:X", "?:A", ["$ctxt", "?:T", "W3", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["can", "?:X", "?:A", ["$ctxt", "?:T", "W3", "?:L", "?:K"]]]]
    ]
  },

  // Default persistence of "has part" across world states
  // W0 -> W1
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has part", "?:X", "?:Y", ["$ctxt", "?:T", "W0", "?:L", "?:K"]],
      ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]]]]
    ]
  },
  // W1 -> W2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has part", "?:X", "?:Y", ["$ctxt", "?:T", "W1", "?:L", "?:K"]],
      ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "W2", "?:L", "?:K"]]]]
    ]
  },
  // W2 -> W3
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has part", "?:X", "?:Y", ["$ctxt", "?:T", "W2", "?:L", "?:K"]],
      ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "W3", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "W3", "?:L", "?:K"]]]]
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

  /*
  
  // these two look like failed attempts of the superset counting rule
[
  ["-=", "?:N", ["$count", ["$setof", "?:Var", "?:ID", ["and", "?:P1", "?:P2"]]]],
  ["$greatereq", ["$count", ["$setof", "?:Var", "?:ID", ["and", "?:P1"]]], "?:N"]
],
[
  ["-=", "?:N", ["$count", ["$setof", "?:Var", "?:ID", ["and", "?:P1", "?:P2", "?:P3"]]]],
  ["$greatereq", ["$count", ["$setof", "?:Var", "?:ID", ["and", "?:P1", "?:P2"]]], "?:N"]
],
  
  */
  
  // the size of a superset of some set S is not less than the size of the set S.
  
  [ ["-=","?:X",["$count",["$setof","?:H","?:J",["$and","?:A","?:B"]]]],  ["$greatereq",["$count",["$setof","?:H","?:J",["$and","?:A"]]],"?:X"] ],
  
  [ ["-=","?:X",["$count",["$setof","?:H","?:J",["$and","?:A","?:B","?:C"]]]],  ["$greatereq",["$count",["$setof","?:H","?:J",["$and","?:A","?:B"]]],"?:X"] ],
  
  [ ["-=","?:X",["$count",["$setof","?:H","?:J",["$and","?:A","?:B","?:C"]]]],  ["$greatereq",["$count",["$setof","?:H","?:J",["$and","?:A","?:C"]]],"?:X"] ],
  
  [ ["-=","?:X",["$count",["$setof","?:H","?:J",["$and","?:A","?:B","?:C"]]]],  ["$greatereq",["$count",["$setof","?:H","?:J",["$and","?:A"]]],"?:X"] ],
   
   
/*

[
[["=",2,["$count",["$setof",["isa","car","$arg1"],"c1_John"]]]],

[["-=","?:X",["$count",["$setof",["and","?:Y","?:Z"],"?:U"]]],          ["$greatereq",["$count",["$setof","?:Y","?:U"]],"?:X"]],

[["=",3,["$count",["$setof",["and",["isa","car","$arg1"],["prop","nice","$arg1","$generic","$generic",["$ctxt","Pres",1]]],"c1_John"]]]]
]

John 1 has three nice cars.
  {"@name":"sent_S1","@logic":["isa","person","John 1"]}
  {"@name":"sent_S1","@logic":["=",3,["$count",["$setof","have","John 1",["$and",["$isa","car","$arg1"],["$has_degree_property","nice","$arg1","none","car"]]]]]}
Does John 1 have two cars?
  {"@name":"sent_S2","@logic":[["-$defq0"],["=",2,["$count",["$setof","have","John 1",["$and",["$isa","car","$arg1"]]]]]]}
  {"@name":"sent_S2","@logic":[["-=",2,["$count",["$setof","have","John 1",["$and",["$isa","car","$arg1"]]]]],["$defq0"]]}
  {"@name":"sent_S2","@question":["$defq0"]}

[

["=",3,["$count",["$setof","h","j",["$and","a","b"]]]],
["-=",2,["$count",["$setof","h","j",["$and","a"]]]],

[  ["-=",3,["$count",["$setof","h","j",["$and","a","b"]]]],
   ["$greatereq",["$count",["$setof","h","j",["$and","a"]]],3] ]

]


[
 [["=",2,"b"]],

 [  ["-=",3,"a"], ["$greatereq","b",3] ],
   
 [["=",3,"a"]]   
]

[
 [["=",2,["$count",["$setof","cc","ee"]]]],

 [["-=","?:X",["$count",["$setof",["and","?:Y","?:Z"],"?:U"]]], ["$greatereq",["$count",["$setof","?:Y","?:U"]],"?:X"]],

 [["=",3,["$count",["$setof",["and","cc","dd"],"ee"]]]]
]


[
 [["=",2,["$count","s2"]]],

 [["-=","?:X",["$count","s1"]], ["$greatereq",["$count","s2"],"?:X"]],

 [["=",3,["$count","s1"]]]
]

[
 ["=",2,["$count",["$setof","h","j",["$and","a"]]]],
 
 [ ["-=","?:X",["$count",["$setof","h","j",["$and","a","b"]]]],  ["$greatereq",["$count",["$setof","h","j",["$and","a"]]],"?:X"] ],
   
 ["=",3,["$count",["$setof","h","j",["$and","a","b"]]]]
 
]

[
 [["=",2,["$count",["$setof","have","John 1",["$and",["$isa","car","$arg1"]]]]]],
 
 [ ["-=","?:X",["$count",["$setof","?:H","?:J",["$and","?:A","?:B"]]]],  ["$greatereq",["$count",["$setof","?:H","?:J",["$and","?:A"]]],"?:X"] ],

 ["=",3,["$count",["$setof","have","John 1",["$and",["$isa","car","$arg1"],["$has_degree_property","nice","$arg1","none","car"]]]]]
]

*/


  // == 7b. DEFINITE FUNCTION TERMS ($theof1) ==
  // Generic possession bridge: John has $theof1("father", John, CT)
  [["have", "?:S", ["$theof1", "?:R", "?:S", "?:C"], "?:C"]],
  // Note: isa bridge is generated per-relation in logconvert to avoid
  // spurious answers (a generic isa bridge would make $theof1(R,S,C) an R
  // for any R and S, creating infinite witnesses for wh-queries).

  // == 8. MEASUREMENTS & ATTRIBUTES ==
  // Value Holders [cite: 306, 307]
  [["isa", "weight", ["$theof1", "weight", "?:O", "?:Ctxt"]]],
  [["isa", "price", ["$theof1", "price", "?:O", "?:Ctxt"]]],
  [["isa", "length", ["$theof1", "length", "?:O", "?:Ctxt"]]],
  // Property to Attribute Mapping
  [
    ["-has degree property", "red", "?:X", "none", "?:Rel", "?:Ctxt"],
    ["is rel2", "color of", "red", "?:X", "?:Ctxt"]
  ],
  
  // == 11. WORLD GRAPH GEOMETRY ==

// Axiom 1: Direct succession implies "before"

[["next", "W0", "W1"]],

[
  ["-next", "?:W_prev", "?:W_curr"],
  ["before", "?:W_prev", "?:W_curr"]
],

// Axiom 2: Transitivity of "before" (W0 < W1, W1 < W2 => W0 < W2)
[
  ["-before", "?:W1", "?:W2"],
  ["-before", "?:W2", "?:W3"],
  ["before", "?:W1", "?:W3"]
],

  // == 12. TENSE MIGRATION BRIDGES ==
/*
[
  ["-has degree rel2","?:R","?:X","?:Y","?:Z","?:U",["$ctxt","present","W0","?:Fv1","?:Fv2"]],
  ["has degree rel2","?:R","?:X","?:Y","?:Z","?:U",["$ctxt","past","W1","?:Fv1","?:Fv2"]]
],
*/
// --- Flat Predicates ---

// has property
[
  ["-has property", "?:P", "?:X", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has property", "?:P", "?:X", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// have
[
  ["-have", "?:O", "?:X", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["have", "?:O", "?:X", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// has part
[
  ["-has part", "?:W", "?:P", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has part", "?:W", "?:P", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// is rel2
[
  ["-is rel2", "?:R", "?:E1", "?:E2", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["is rel2", "?:R", "?:E1", "?:E2", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// can (capability)
[
  ["-can", "?:X", "?:Act", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["can", "?:X", "?:Act", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// --- Gradable Predicates ---

// has degree property
[
  ["-has degree property", "?:P", "?:X", "?:D", "?:RC", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has degree property", "?:P", "?:X", "?:D", "?:RC", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// has degree rel2
[
  ["-has degree rel2", "?:R", "?:E1", "?:E2", "?:D", "?:RC", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has degree rel2", "?:R", "?:E1", "?:E2", "?:D", "?:RC", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// --- Davidsonian Roles (Track 2) ---

// isa, has type, has actor, has target
// These propagate the context change to ensure the whole event structure matches.
[
  ["-isa", "?:Type", "?:E", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["isa", "?:Type", "?:E", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],
[
  ["-has type", "?:E", "?:T", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has type", "?:E", "?:T", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],
[
  ["-has actor", "?:E", "?:A", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has actor", "?:E", "?:A", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],
[
  ["-has target", "?:E", "?:T", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has target", "?:E", "?:T", ["$ctxt", "past", "?:W_new", "?:L", "?:K"]]
],

// Special: has time (Explicit Davidsonian Tense Role)
// If E was 'present' in W_old, it is 'past' in the context of W_new.
[
  ["-has time", "?:E", "present", "?:Prep_t", ["$ctxt", "present", "?:W_old", "?:L", "?:K"]],
  ["-before", "?:W_old", "?:W_new"],
  ["has time", "?:E", "past", "?:Prep_t", ["$ctxt", "present", "?:W_new", "?:L", "?:K"]]
],

// experimental
/*
 [["-isa","head","?:Y"],
  ["-has part","?:X","?:Y","?:C"],
  ["is rel2","head of","?:Y","?:X","?:C"]
 ],
 
 [["-isa","head","?:Y"],
  ["-is rel2","head of","?:Y","?:X","?:C"]
 ],
 
 [["has part","?:X","?:Y","?:C"],
  ["-is rel2","head of","?:Y","?:X","?:C"]
 ]
*/


// == 13. TEMPORAL-WORLD INTEGRATION & FUNCTIONAL EXTRACTORS ==

// --- A. $get_world "Destructor" ---
// This makes the function usable by allowing the prover to unify the 
// second element of a context term with a variable.
[ ["=", "?:W", ["$get_world", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]]] ],

// --- B. $theof1/datetime Year to Semantic Tense Bridge ---
// When a world's time (via $theof1) is a $datetime value less than current year,
// infer the world is in the past.
[
  ["-=", ["$theof1", "time", "?:W", "?:C"], ["$datetime", "?:T"]],
  ["-$less", "?:T", 2026],
  ["is_past_world", "?:W"]
],

// --- D. Context Tense Normalization ---
// If a world is determined to be in the past, any fact holds in that 
// world also satisfies a context of "past".
[
  ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],

// Repeat D for other core predicates to ensure universal tense matching
[
  ["-has actor", "?:E", "?:A", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has actor", "?:E", "?:A", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has type", "?:E", "?:V", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has type", "?:E", "?:V", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has target", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has target", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has location", "?:E", "?:P", "?:Prep", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has location", "?:E", "?:P", "?:Prep", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has time", "?:E", "?:T2", "?:Prep", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has time", "?:E", "?:T2", "?:Prep", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has property", "?:P", "?:X", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has property", "?:P", "?:X", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has degree property", "?:P", "?:X", "?:D", "?:R", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has degree property", "?:P", "?:X", "?:D", "?:R", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-have", "?:X", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["have", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has part", "?:X", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has part", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-can", "?:X", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["can", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
]
]
