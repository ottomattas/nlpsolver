# Small test file for quick experimentation — 3 tests.
# Format: [text, expected_answer, optional_extra_info]
# expected_answer: True / False / None / "Answer string."
# optional_extra_info: unused by the runner for now

[
  # yes/no — should be True
  ["""Elephants are animals. John is an elephant. John is an animal?""", True],

  # yes/no — should be False
  ["""Elephants are not birds. John is an elephant. John is a bird?""", False],

  # wh-question
  ["""Elephants are animals. John is an elephant. Who is an animal?""", """John."""],
]
