# Defeasible / nonmonotonic reasoning subset (extension X3).
#
# 10 cases drawn verbatim from tests_core.py, sections DEFAULT & DEFEASIBLE
# REASONING and DEFAULTS WITH EXCEPTIONS (BLOCKING) -- the phenomena where a
# general default ("birds fly") is overridden by a specific exception
# ("penguins do not fly"), which gk handles via its nonmonotonic blocker
# mechanism but which has no sound one-shot first-order encoding.
#
# Used to test whether the two-stage advantage CONCENTRATES on defeasible
# reasoning: run Condition A (two-stage) vs C (one-stage direct) on this set.
# ids/expected match tests_core.py exactly, so results are directly comparable.

[

  [1407, 'Penguins are birds who do not fly. Birds fly. John is a penguin. John flies?', False],
  [1408, 'Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John flies?', False],
  [1424, 'Penguins are birds. Penguins do not fly. Birds fly. Penguins fly?', False],
  [1426, 'Penguins are birds. Penguins do not fly. Birds fly. Who does not fly?', 'A penguin.'],
  [1427, 'Penguins are birds. Penguins do not fly. Birds fly. John is a penguin. John is a bird?', True],
  [1429, 'Birds fly and eat. Baby birds do not fly. John is a baby bird. Mike is a bird.\n    John does not fly?', True],
  [1446, 'Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John can fly?', False],
  [1447, 'Birds fly. No penguin can fly. Penguins are birds. John is a penguin. John flies?', False],
  [1449, 'Birds fly. No penguin can fly. Penguins are birds. John is a bird. John can fly?', True],
  [1458, 'Birds can fly. Baby birds do not fly. John is a baby bird. Mike is a bird. Who can not fly?', 'John.'],
]
