GK User Guide
==============

GK is a commonsense reasoner for first-order logic enhanced with
confidence values and default rules with exceptions.

Platforms
---------

Two prebuilt binaries ship with this folder:

  * `gk` — statically-linked Linux x86-64 ELF, ready to run.
  * `gk-macos-ARM64.zip` — macOS on Apple Silicon (ARM64) build.  Unzip
    it and use the extracted `gk` binary in place of the Linux one.

The `nlpsolver` pipelines (`llmpipe` and `udppipe`) that drive `gk` have
only been tested on Linux; running them on macOS has not been verified
and may need small tweaks.  For other platforms, build from
[gkc](https://github.com/tammet/gkc) — the gkc-based source that
`gk` is built on.


What GK Does
------------

GK answers questions about knowledge expressed as logical rules and facts.
It handles three kinds of reasoning:

  1. **Classical logic**: derive conclusions from facts and rules
  2. **Uncertain reasoning**: track confidence values through derivations
  3. **Default reasoning**: apply rules that are "typically true" but
     can have exceptions (e.g., "birds fly, but penguins don't")


Quick Start
-----------

Run an example:

    ./gk Examples/core/grandfather.js

GK reads a JSON file containing facts, rules, and a question,
then searches for proofs and prints answers with confidence values.

The output is one flat JSON document (newline-separated, not indented).
For the `grandfather.js` example you get something like:

    {"result": "answer found",

    "answers": [
    {
    "answer": [["$ans","mark"]],
    "confidence": 0.684,
    "positive proof":
    [
    [1, ["in", "frm_3", "axiom", 0.95], [["-father","?:X","?:Y"], ["-father","?:Z","?:X"], ["grandfather","?:Z","?:Y"]]],
    [2, ["in", "frm_2", "axiom", 0.8], [["father","pete","mark"]]],
    [3, ["mp", 1, 2, "fromaxiom", 0.76], [["-father","?:X","pete"], ["grandfather","?:X","mark"]]],
    [4, ["in", "frm_1", "axiom", 0.9], [["father","john","pete"]]],
    [5, ["mp", 3, 4, "fromaxiom", 0.684], [["grandfather","john","mark"]]],
    [6, ["in", "frm_4", "goal", 1], [["-grandfather","john","?:X"], ["$ans","?:X"]]],
    [7, ["mp", 5, 6, "fromgoal", 0.684], [["$ans","mark"]]]
    ]}
    ]}

The key fields are:
  * `"result"` — whether an answer was found
  * `"answer"` — the answer term(s)
  * `"confidence"` — confidence value (0.0 to 1.0)
  * `"positive proof"` — the derivation steps


Input Format
------------

GK reads JSON files (`.js` extension) in JSON-LD-LOGIC format.
C-style comments (`//` and `/* */`) are supported.

### Facts

    ["bird","tweety"]

### Rules

    [["bird","?:X"], "=>", ["flies","?:X"]]

Variables start with `?:` (e.g., `?:X`, `?:Name`).

### Questions

    {"@question": ["flies","tweety"]}

Or with answer variables — any free variable in the question is
collected as an answer binding:

    {"@question": ["flies","?:X"]}

### Confidence values

    {"@logic": ["bird","tweety"], "@confidence": 0.9}

Values range from 0.0 (uncertain) to 1.0 (certain).
Integers 2-100 are treated as percentages (e.g., 90 means 0.9).

### Default rules with exceptions

    {"@logic": [["-bird","?:X"],["flies","?:X"],
                 ["$block", 1, ["$not", ["flies","?:X"]]]]}

The `$block` literal marks this as a defeasible rule. A rule with
higher strength number overrides one with lower strength.

For full format details, see `Doc/json_ld_logic.md`.


Examples
--------

Examples are organized in `Examples/` by category:

### Core logic (`Examples/core/`)

Basic facts, rules, queries, equality, and lists. No confidence
or default rules.

    ./gk Examples/core/grandfather.js     # rule-based inference
    ./gk Examples/core/algebra.js         # equality reasoning
    ./gk Examples/core/lists.js           # list operations
    ./gk Examples/core/negation.js        # negation

### Confidence values (`Examples/confidences/`)

Reasoning with uncertain knowledge. GK tracks positive and negative
evidence and cumulates confidence from multiple proofs.

    ./gk Examples/confidences/conf1.js          # positive + negative evidence
    ./gk Examples/confidences/cumulate.js        # cumulation from multiple proofs
    ./gk Examples/confidences/rulemult.js         # confidence multiplication
    ./gk Examples/confidences/alarm.js            # burglary/alarm problem
    ./gk Examples/confidences/smokes.js           # social smoking network
    ./gk Examples/confidences/socialsmoking.js    # larger social network
    ./gk Examples/confidences/near.js             # transitive chain decay

### Default rules with exceptions (`Examples/exceptions/`)

Rules that are typically true but can be overridden by more specific
exceptions.

    ./gk Examples/exceptions/trivial.js           # simplest default
    ./gk Examples/exceptions/bird_penguin.js       # birds fly, penguins don't
    ./gk Examples/exceptions/penguin2.js           # deep hierarchy, integer priorities
    ./gk Examples/exceptions/penguin3.js -defaults -datafolder Examples/exceptions    # same hierarchy, taxonomy-based priorities
    ./gk Examples/exceptions/classify.js           # classification
    ./gk Examples/exceptions/nixon.js              # competing equal-strength defaults
    ./gk Examples/exceptions/people_room.js        # situation calculus
    ./gk Examples/exceptions/partcapability2.js    # part-capability reasoning
    ./gk Examples/exceptions/gbirds.js             # scalability example

With taxonomy-based default comparison (requires data files):

    ./gk Examples/exceptions/taxonomy.js -defaults -datafolder Examples/exceptions

### Strategy files (`Examples/strategy/`)

Strategy files control proof search. Use with `-strategy`:

    ./gk Examples/core/algebra.js -strategy Examples/strategy/runs.txt

See `Examples/README.md` for descriptions of every example file.


Common Command-Line Options
----------------------------

    ./gk <file>                   basic proof search
    ./gk <file> -seconds 30       time limit (default: 10 seconds)
    ./gk <file> -print 15         more verbose output (default: 10)
    ./gk <file> -confidence 0.2   lower confidence threshold (default: 0.1)
    ./gk <file> -firstanswer      stop after first answer
    ./gk <file> -defaults         use taxonomy for default comparison
    ./gk <file> -nonegative       skip negative evidence
    ./gk -help                    show all options

### Output formats

    ./gk <file>                   JSON output (default)
    ./gk <file> -tptp             TPTP format output

### Shared memory knowledge base

For large knowledge bases, load once and query multiple times:

    ./gk axioms.js -readkb -mbsize 2000
    ./gk query.js -usekb
    ./gk -deletekb

See `Doc/cli_reference.md` for the complete command-line reference.


Understanding Results
---------------------

GK reports one of these results:

    "answer found"
        One or more answers with confidence above the threshold.

    "evidence below limit"
        Proofs found but confidence too low. Try `-confidence 0`.

    "evidence for candidate answers below limit"
        Candidate answers found but blocked or reduced by negative evidence.

    "generic assumptions contradicted"
        The question's assumptions lead to a contradiction.

    "no information"
        No relevant facts or rules found for the question.

    "no answers found"
        Search completed without finding proofs.

    "time limit, proof not found"
        Ran out of time. Try `-seconds 60`.


How Confidence Works
--------------------

Each fact and rule can have a confidence value. When GK derives
a new fact from premises, the derived confidence is the minimum
of the premise confidences.

GK collects both positive evidence (proofs something is true) and
negative evidence (proofs something is false). The final confidence is:

    final = positive_confidence - negative_confidence

When multiple independent proofs support the same conclusion,
their confidences are cumulated (combined).


How Default Rules Work
----------------------

Default rules use `$block` to mark exceptions:

    [["-bird","?:X"],["flies","?:X"],
     ["$block", 1, ["$not", ["flies","?:X"]]]]

This says: "if X is a bird, then X flies, UNLESS something with
strength > 1 says X does not fly."

A penguin exception with strength 2 overrides the bird default:

    [["-penguin","?:X"],["-flies","?:X"],
     ["$block", 2, ["flies","?:X"]]]

GK checks proofs in four phases:
  1. Find candidate proofs for the question
  2. Check blockers on candidates
  3. Find negative evidence
  4. Check blockers on negative evidence


Writing Your Own Problems
-------------------------

Create a `.js` file with this structure:

    [
      // Facts
      ["bird","tweety"],
      ["penguin","pete"],

      // Rules
      [["penguin","?:X"], "=>", ["bird","?:X"]],

      // Rules with confidence
      {"@logic": [["bird","?:X"], "=>", ["flies","?:X"]],
       "@confidence": 0.9},

      // Default rules with exceptions
      {"@logic": [["-bird","?:X"],["flies","?:X"],
                   ["$block", 1, ["$not", ["flies","?:X"]]]]},

      // Question (free variable ?:X collects answers)
      {"@question": ["flies","?:X"]}
    ]

Run it:

    ./gk myfile.js

Tips:
  * Start simple — add complexity gradually
  * Use the examples as templates
  * Check output with `-print 15` for more detail
  * If no answer, try increasing time with `-seconds 30`
  * If "evidence below limit", try `-confidence 0`


Further Documentation
---------------------

  * `Examples/README.md` — Detailed guide to all examples
  * `Doc/tutorial.md` — Full tutorial with 9 parts
  * `Doc/json_ld_logic.md` — Complete input format specification
  * `Doc/cli_reference.md` — All command-line options
  * `Doc/strategy_reference.md` — Strategy file parameters
  * https://logictools.org/gk/ — Online documentation
  * https://logictools.org/gk/tutorial.html — Online tutorial


Papers
------

  * T. Tammet: GKC: a reasoning system for large knowledge bases. CADE 2019.
  * T. Tammet, D. Draheim, P. Jarv: Confidences for commonsense reasoning. CADE 2021.
  * T. Tammet, D. Draheim, P. Jarv: GK: implementing full first order
    default logic for commonsense reasoning. IJCAR 2022.
