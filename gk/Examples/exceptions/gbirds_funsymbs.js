// Birds-fly with function symbols
// ASP systems cannot handle this; gk solves it in < 1 second
// (see https://logictools.org/gk/ for comparison results)
//
// Run: ./gk Examples/exceptions/gbirds_funsymbs.js

[

["bird","b1"],
["penguin","p1"],

[["penguin","?:X"],"=>",["bird","?:X"]],
[["-bird","?:X"],["flies","?:X"], ["$block", 3, ["$not", ["flies", "?:X"]]]],
[["penguin","?:X"],"=>",["-flies","?:X"]],

[["penguin","?:X"],"=>",["penguin",["f","?:X"]]],
[["bird","?:X"],"=>",["bird",["f","?:X"]]],

{"@question": ["flies","b1"]}

]
