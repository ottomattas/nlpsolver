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

  // == 3.1 COMPARATIVE ASYMMETRY ==
  // A strict comparative cannot hold in both directions simultaneously.
  // fast(X,Y,high) ∧ fast(Y,X,high) → contradiction
  [
    ["-has degree rel2", "?:R", "?:X", "?:Y", "high", "?:RC1", "?:C1"],
    ["-has degree rel2", "?:R", "?:Y", "?:X", "high", "?:RC2", "?:C2"]
  ],
  // Strict measurement order is asymmetric: less(M1,M2) ∧ less(M2,M1) → contradiction
  [
    ["-less_measure", "?:M1", "?:M2"],
    ["-less_measure", "?:M2", "?:M1"]
  ],
  // Equal measures exclude strict ordering in both directions.
  [
    ["-=", "?:M1", "?:M2"],
    ["-less_measure", "?:M1", "?:M2"]
  ],
  [
    ["-=", "?:M1", "?:M2"],
    ["-less_measure", "?:M2", "?:M1"]
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
  
  // Spatial hierarchy: "on" and "in" both imply "at" (general co-location).
  // "on" does NOT imply "in" (surface contact ≠ containment).
  [["-is rel2", "on", "?:X", "?:Y", "?:Ctxt"], ["is rel2", "at", "?:X", "?:Y", "?:Ctxt"]],
  [["-is rel2", "in", "?:X", "?:Y", "?:Ctxt"], ["is rel2", "at", "?:X", "?:Y", "?:Ctxt"]],

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
  // Result tense is "present" (at the new world), not copied from the source event.
  // Uses variable worlds with next(?:W, ?:W2) precondition.
  [
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has type", "?:E", "go", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has destination", "?:E", "?:Dest", "?:Prep", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-next", "?:W", "?:W2"],
    ["is rel2", "at", "?:X", "?:Dest", ["$ctxt", "present", "?:W2", "?:L", "?:K"]]
  ],
  // Movement also works with has_direction (synonym for has_destination in some parses)
  [
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has type", "?:E", "go", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has direction", "?:E", "?:Dest", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-next", "?:W", "?:W2"],
    ["is rel2", "at", "?:X", "?:Dest", ["$ctxt", "present", "?:W2", "?:L", "?:K"]]
  ],
  /*
  // Movement retraction (OLD, replaced by moved+$block approach):
  // after moving to Dest, X is no longer at any previous location Y
  // (unless Y = Dest, i.e. moved to the same place). This provides evidence for $block
  // on the frame axiom, preventing old locations from persisting.
  [
    ["-is rel2", "at", "?:X", "?:Y", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T2", "?:W", "?:L2", "?:K2"]],
    ["-has type", "?:E", "go", ["$ctxt", "?:T2", "?:W", "?:L2", "?:K2"]],
    ["-has destination", "?:E", "?:Dest", "?:Prep", ["$ctxt", "?:T2", "?:W", "?:L2", "?:K2"]],
    ["-next", "?:W", "?:W2"],
    ["=", "?:Y", "?:Dest"],
    ["-is rel2", "at", "?:X", "?:Y", ["$ctxt", "present", "?:W2", "?:L", "?:K"]]
  ],
  */

  // Derive moved(X, W): X performed a movement event at world W.
  // Used by the is_rel2 frame axiom to block location persistence when X moved.
  // Only the "go" version is needed: lc_rewrites.py normalizes travel/journey/
  // move to "go" before clauses reach the prover (avoids synonym axiom chains).
  [["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["-has type", "?:E", "go", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["moved", "?:X", "?:W"]],
  /*
  // Redundant with pipeline normalization in lc_rewrites.py:
  [["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["-has type", "?:E", "travel", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["moved", "?:X", "?:W"]],
  [["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["-has type", "?:E", "journey", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["moved", "?:X", "?:W"]],
  [["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["-has type", "?:E", "move", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["moved", "?:X", "?:W"]],
  */

  // Movement Synonyms — REDUNDANT, kept commented for documentation.
  // lc_rewrites.py rewrites travel/journey/move → go pre-clausification,
  // so the prover never sees these verbs. Pipeline normalization avoids
  // synonym axiom chains that cause combinatorial explosion with many worlds.
  /*
  [["-has type", "?:E", "travel", "?:Ctxt"], ["has type", "?:E", "go", "?:Ctxt"]],
  [["-has type", "?:E", "journey", "?:Ctxt"], ["has type", "?:E", "go", "?:Ctxt"]],
  [["-has type", "?:E", "move", "?:Ctxt"], ["has type", "?:E", "go", "?:Ctxt"]],
  */

  // Placement Results: If X 'put's Target at Dest, Target is 'at' Dest in the next state.
  // Mirrors the movement result axiom above, but the TARGET (not the actor) ends
  // up at the destination. Pattern: "Tom put the book on the chair" → book is at chair.
  [
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has type", "?:E", "put", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has target", "?:E", "?:Obj", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has destination", "?:E", "?:Dest", "?:Prep", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-next", "?:W", "?:W2"],
    ["is rel2", "?:Prep", "?:Obj", "?:Dest", ["$ctxt", "present", "?:W2", "?:L", "?:K"]]
  ],

  // == 5b. TRANSFER RESULTS ==
  // If X 'give's Target to Recipient, Recipient 'have's Target in the next state.
  // Pattern follows movement result axiom above.
  [
    ["-has actor", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has type", "?:E", "give", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has recipient", "?:E", "?:Recip", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has target", "?:E", "?:Obj", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-next", "?:W", "?:W2"],
    ["have", "?:Recip", "?:Obj", ["$ctxt", "present", "?:W2", "?:L", "?:K"]]
  ],

  // Derive transferred(Obj, W): object was transferred away at world W.
  // Used by "have" frame axiom to block giver's possession from persisting.
  [["-has type", "?:E", "give", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["-has target", "?:E", "?:Obj", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
   ["transferred", "?:Obj", "?:W"]],

  // == 5c. PERSPECTIVE BRIDGES (GIVE/RECEIVE) ==
  // Give and receive describe the same event from different perspectives.
  // Only give→receive direction to avoid circular role pollution.
  // (receive→give is handled by pipeline normalization in lc_rewrites.py.)
  // Type bridge: a give event is also a receive event.
  [["-has type", "?:E", "give", "?:Ctxt"],
   ["has type", "?:E", "receive", "?:Ctxt"]],
  // Role mapping: the recipient of the give is the actor of the receive.
  [["-has type", "?:E", "give", "?:Ctxt"],
   ["-has recipient", "?:E", "?:X", "?:Ctxt"],
   ["has actor", "?:E", "?:X", "?:Ctxt"]],

  // Transfer verb synonyms — REDUNDANT, kept commented for documentation.
  // lc_rewrites.py rewrites hand/pass/send → give pre-clausification.
  /*
  [["-has type", "?:E", "hand", "?:Ctxt"], ["has type", "?:E", "give", "?:Ctxt"]],
  [["-has type", "?:E", "pass", "?:Ctxt"], ["has type", "?:E", "give", "?:Ctxt"]],
  [["-has type", "?:E", "send", "?:Ctxt"], ["has type", "?:E", "give", "?:Ctxt"]],
  */

  // == 5d. COMPLETION RESULT STATES ==
  // If a "finish" event targets X, then X has property "finished" in the next state.
  [
    ["-has type", "?:E", "finish", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-has target", "?:E", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
    ["-next", "?:W", "?:W2"],
    ["has property", "finished", "?:X", ["$ctxt", "present", "?:W2", "?:L", "?:K"]]
  ],

  // == 5e. PP-ATTACHMENT BRIDGES ==
  // Bridge: instrument implies possession by the actor (defeasible, 90%).
  // "The man saw the woman with a telescope" → the man had the telescope.
  {
    "@confidence": 0.9,
    "@logic": [
      ["-has instrument", "?:E", "?:X", "?:Ctxt"],
      ["-has actor", "?:E", "?:Y", "?:Ctxt"],
      ["have", "?:Y", "?:X", "?:Ctxt"],
      ["$block", 0, ["$not", ["have", "?:Y", "?:X", "?:Ctxt"]]]
    ]
  },
  // Bridge: event location implies target location (defeasible, 90%).
  // "John ate the pizza on the table" → the pizza was on the table.
  {
    "@confidence": 0.9,
    "@logic": [
      ["-has location", "?:E", "?:L", "?:P", "?:Ctxt"],
      ["-has target", "?:E", "?:Y", "?:Ctxt"],
      ["is rel2", "?:P", "?:Y", "?:L", "?:Ctxt"],
      ["$block", 0, ["$not", ["is rel2", "?:P", "?:Y", "?:L", "?:Ctxt"]]]
    ]
  },

  // == 6. PERSISTENCE (FRAME PROBLEM) ==
  // Default persistence across world states using variable worlds with next(?:W, ?:W2).
  // Each predicate persists defeasibly ($block) unless overridden.

  /*
  // is rel2 (OLD: general $not block — replaced by moved-based block)
  {
    "@confidence": 0.99,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]]]]
    ]
  },
  */

  // is rel2 persistence: blocked when X moved (go-event) at that world.
  // This prevents old locations from persisting after movement while allowing
  // non-movement is_rel2 relations (like "afraid of") to persist normally
  // (since moved(X,W) is only derived from go-events, not from other relations).
  {
    "@confidence": 0.99,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["moved", "?:X", "?:W"]]
    ]
  },

  // have: blocked when the possessed object was transferred at that world.
  {
    "@confidence": 0.99,
    "@logic": [
      ["-have", "?:Y", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["have", "?:Y", "?:X", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["transferred", "?:X", "?:W"]]
    ]
  },
  // has property
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has property", "?:P", "?:X", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["has property", "?:P", "?:X", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has property", "?:P", "?:X", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]]]]
    ]
  },
  // has degree property
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree property", "?:P", "?:X", "?:D", "?:C", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]]]]
    ]
  },
  // can
  {
    "@confidence": 0.99,
    "@logic": [
      ["-can", "?:X", "?:A", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["can", "?:X", "?:A", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["can", "?:X", "?:A", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]]]]
    ]
  },
  // has part
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has part", "?:X", "?:Y", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has part", "?:X", "?:Y", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]]]]
    ]
  },
  // has degree rel2
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "?:T", "?:W", "?:L", "?:K"]],
      ["-next", "?:W", "?:W2"],
      ["has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "?:T", "?:W2", "?:L", "?:K"]]]]
    ]
  },

  // == 6a. SAME-WORLD TENSE BRIDGE: past@W → present@W (defeasible) ==
  // DISABLED: replaced by question-specific bridge axioms generated in
  // logconvert.py (build_question_tense_bridges). The dynamic axioms
  // pin entity arguments to what the question actually mentions, so the
  // prover only chains past->present for those specific entities — much
  // smaller search space than the global axioms below.
  /*
  // have
  {
    "@confidence": 0.97,
    "@logic": [
      ["-have", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["have", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["have", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  // has part
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has part", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["has part", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has part", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  // can
  {
    "@confidence": 0.99,
    "@logic": [
      ["-can", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["can", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["can", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  // has property
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has property", "?:P", "?:X", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["has property", "?:P", "?:X", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has property", "?:P", "?:X", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  // has degree property
  {
    "@confidence": 0.99,
    "@logic": [
      ["-has degree property", "?:P", "?:X", "?:D", "?:RC", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["has degree property", "?:P", "?:X", "?:D", "?:RC", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree property", "?:P", "?:X", "?:D", "?:RC", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  // is rel2
  {
    "@confidence": 0.95,
    "@logic": [
      ["-is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["is rel2", "?:R", "?:X", "?:Y", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  // has degree rel2
  {
    "@confidence": 0.95,
    "@logic": [
      ["-has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "past", "?:W", "?:L", "?:K"]],
      ["has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
      ["$block", 0, ["$not", ["has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "present", "?:W", "?:L", "?:K"]]]]
    ]
  },
  */

  /*
  // == 6b. SPATIAL MUTUAL EXCLUSION (experimental, commented out) ==
  // If X is at two locations at the same world, and both are rooms of specific
  // types known to be different, then they must be equal (contradiction via
  // inequality facts).  Requires inequality axioms between room classes.

  // Exclusion: two room locations for same person at same world must be equal
  {"@logic": [
    ["=", "?:Loc1", "?:Loc2"],
    ["-isa", "room", "?:Loc1"],
    ["-isa", "room", "?:Loc2"],
    ["-is rel2", "at", "?:X", "?:Loc1", ["$ctxt", "present", "?:W", "?:L", "?:K"]],
    ["-is rel2", "at", "?:X", "?:Loc2", ["$ctxt", "present", "?:W", "?:L", "?:K"]]
  ], "@name": "ax_room_exclusion"},

  // Room class inequality: entities of different room classes are distinct.
  // These would need to be generated programmatically for each pair of room
  // classes present in the input, or derived from a taxonomy.
  // Example pairs (would be generated per problem):
  [
    ["-isa", "hallway", "?:X"],
    ["-isa", "kitchen", "?:Y"],
    ["-=", "?:X", "?:Y"]
  ],
  [
    ["-isa", "hallway", "?:X"],
    ["-isa", "bathroom", "?:Y"],
    ["-=", "?:X", "?:Y"]
  ],
  [
    ["-isa", "kitchen", "?:X"],
    ["-isa", "bathroom", "?:Y"],
    ["-=", "?:X", "?:Y"]
  ],
  // Also need: isa(room, X) for each location entity — could be generated
  // from the isa(hallway, X) etc. via a superclass axiom:
  [["-isa", "hallway", "?:X"], ["isa", "room", "?:X"]],
  [["-isa", "kitchen", "?:X"], ["isa", "room", "?:X"]],
  [["-isa", "bathroom", "?:X"], ["isa", "room", "?:X"]],
  [["-isa", "bedroom", "?:X"], ["isa", "room", "?:X"]],
  [["-isa", "garden", "?:X"], ["isa", "room", "?:X"]],
  [["-isa", "office", "?:X"], ["isa", "room", "?:X"]],
  */

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
  // Note: both the isa and the have bridges are generated per-relation at
  // parse time (isa in logconvert, have via add_possessive_have) so that
  // they are grounded to concrete owners. A generic have bridge like
  //   [["have", "?:S", ["$theof1", "?:R", "?:S", "?:C"], "?:C"]]
  // is universally quantified in S and lets the prover answer any
  // wh-query about possession with a free-variable witness (e.g. "X3"
  // alongside "Tom" for "who had a bicycle?"), so it is intentionally
  // NOT defined here.

  // == 7c. PREPOSITION SUBSUMPTION (spatial) ==
  // Unidirectional specific → general implications for near-synonymous
  // spatial prepositions. "X is under Y" implies "X is below Y", but not
  // vice versa ("below" is more general — no contact implication).
  // Mutual-exclusion between opposites lives below (§7e) as static axioms.
  [["-is rel2", "underneath", "?:X", "?:Y", "?:C"], ["is rel2", "below", "?:X", "?:Y", "?:C"]],
  [["-is rel2", "beneath",    "?:X", "?:Y", "?:C"], ["is rel2", "below", "?:X", "?:Y", "?:C"]],
  [["-is rel2", "under",      "?:X", "?:Y", "?:C"], ["is rel2", "below", "?:X", "?:Y", "?:C"]],
  [["-is rel2", "over",       "?:X", "?:Y", "?:C"], ["is rel2", "above", "?:X", "?:Y", "?:C"]],
  [["-is rel2", "on_top_of",  "?:X", "?:Y", "?:C"], ["is rel2", "above", "?:X", "?:Y", "?:C"]],

  // == 7d. PREPOSITION SUBSUMPTION (temporal) ==
  [["-is rel2", "prior_to",   "?:X", "?:Y", "?:C"], ["is rel2", "before", "?:X", "?:Y", "?:C"]],
  [["-is rel2", "following",  "?:X", "?:Y", "?:C"], ["is rel2", "after",  "?:X", "?:Y", "?:C"]],
  [["-is rel2", "preceding",  "?:X", "?:Y", "?:C"], ["is rel2", "before", "?:X", "?:Y", "?:C"]],

  // == 7e. PREPOSITION MUTUAL EXCLUSION ==
  // Permanent mutual-exclusion between opposite preposition pairs. These
  // are first-class predicates in the standard ontology (they appear as
  // subsumption targets in §7c/7d), so the exclusions hold universally
  // and are emitted statically here rather than by inject_exclusion_axioms.
  // Spatial:
  [["-is rel2", "above",       "?:X", "?:Y", "?:C"], ["-is rel2", "below",       "?:X", "?:Y", "?:C"]],
  [["-is rel2", "over",        "?:X", "?:Y", "?:C"], ["-is rel2", "under",       "?:X", "?:Y", "?:C"]],
  [["-is rel2", "behind",      "?:X", "?:Y", "?:C"], ["-is rel2", "in_front_of", "?:X", "?:Y", "?:C"]],
  [["-is rel2", "inside",      "?:X", "?:Y", "?:C"], ["-is rel2", "outside",     "?:X", "?:Y", "?:C"]],
  [["-is rel2", "left_of",     "?:X", "?:Y", "?:C"], ["-is rel2", "right_of",    "?:X", "?:Y", "?:C"]],
  // Temporal:
  [["-is rel2", "before",      "?:X", "?:Y", "?:C"], ["-is rel2", "after",       "?:X", "?:Y", "?:C"]],
  // Proximity (gradable: positive side any-degree, antonym side "none"
  // intensity, shared RELCLASS — the high→none / low→none intensity
  // bridges in §9 propagate the negation across all intensities).
  [
    ["-has degree rel2", "near",     "?:X", "?:Y", "?:D",  "?:RC", "?:C"],
    ["-has degree rel2", "far_from", "?:X", "?:Y", "none", "?:RC", "?:C"]
  ],
  [
    ["-has degree rel2", "far_from", "?:X", "?:Y", "?:D",  "?:RC", "?:C"],
    ["-has degree rel2", "near",     "?:X", "?:Y", "none", "?:RC", "?:C"]
  ],

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

// Axiom 1: Direct succession implies "before".
//
// The concrete W0..Wn `next` chain that used to live here is now generated
// dynamically by lc_postprocess.inject_world_geometry, based on which world
// constants (W0, W1, ...) actually appear in the per-sentence clauses. Only
// the minimal chain spanning the observed worlds is emitted, so the `before`
// transitivity closure stays small when a problem touches only a few worlds.

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

// --- D. Context Tense Normalization (datetime-triggered only) ---
// When is_past_world(W) holds (currently only via explicit $datetime < 2026),
// rewrite any-tense facts at W to past tense. Does NOT handle the common case
// of LLM tense mismatch (present vs past on the same world without $datetime).
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
],
[
  ["-has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has degree rel2", "?:R", "?:X", "?:Y", "?:D", "?:RC", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has destination", "?:E", "?:Y", "?:Prep", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has destination", "?:E", "?:Y", "?:Prep", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has recipient", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has recipient", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has source", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has source", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has beneficiary", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has beneficiary", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has accompaniment", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has accompaniment", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has path", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has path", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has result", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has result", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has topic", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has topic", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],
[
  ["-has cause", "?:E", "?:Y", ["$ctxt", "?:AnyTense", "?:W", "?:L", "?:K"]],
  ["-is_past_world", "?:W"],
  ["has cause", "?:E", "?:Y", ["$ctxt", "past", "?:W", "?:L", "?:K"]]
],

// experimentally defining the comparison between measures

[
  ["-=", "?:M1", ["$list", "?:N1", "?:U"]],
  ["-=", "?:M2", ["$list", "?:N2", "?:U"]],
  ["-$less", "?:N1", "?:N2"],
  ["less_measure", "?:M1", "?:M2"]
],

[
  ["-less_measure", "?:M1", "?:M2"],
  ["-=", "?:M1", ["$list", "?:N1", "?:U"]],
  ["-=", "?:M2", ["$list", "?:N2", "?:U"]],
  ["$less", "?:N1", "?:N2"]
],

[
  ["-$less", "?:N1", "?:N2"],
  ["less_measure", ["$list", "?:N1", "?:U"], ["$list", "?:N2", "?:U"]]
],

[
  ["-less_measure", ["$list", "?:N1", "?:U"], ["$list", "?:N2", "?:U"]],
  ["$less", "?:N1", "?:N2"]
]

]
