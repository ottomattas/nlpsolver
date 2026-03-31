// Basic birds-fly/penguins-don't default logic example
// Used as baseline for ASP system comparison
// (see https://logictools.org/gk/ for comparison results)
//
// Run: ./gk Examples/exceptions/gbirds.js

[

["bird","b1"],
["penguin","p1"],

[["penguin","?:X"],"=>",["bird","?:X"]],
[["-bird","?:X"],["flies","?:X"], ["$block", 3, ["$not", ["flies", "?:X"]]]],
[["penguin","?:X"],"=>",["-flies","?:X"]],

{"@question": ["flies","b1"]}

]
