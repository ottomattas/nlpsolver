GK Tutorial
===========

GK is a commonsense reasoner for first-order logic enhanced with
confidence values, default rules with exceptions, and word similarities.

This tutorial assumes you have compiled gk (see README.md for instructions)
and have the `gk` binary in the top folder.

See also https://logictools.org/gk/ and https://logictools.org/gk/tutorial.html
for an online version with additional examples.


Overview
--------

GK is built in three layers:

  * **gkc** (gk core): a high-performance classical first-order logic prover
    using resolution and paramodulation. See https://github.com/tammet/gkc
  * **confer** (confidence layer): extends gkc with numeric confidence values
    for facts and rules, combining evidence from multiple derivations
  * **gk** (top layer): adds default rules with exceptions (blockers),
    word similarity matching, and large knowledge graph integration

GK accepts input in JSON-LD-LOGIC format (files use the `.js` extension).
See `Doc/json_ld_logic.md` for the format specification.


Quick Start
-----------

Run a simple example:

    ./gk Examples/exceptions/trivial.js

This proves a basic logical implication and outputs the proof with
an answer and its confidence value.

Examples are organized in `Examples/` subfolders by category:

  * `Examples/core/` - basic logic (facts, rules, queries, equality)
  * `Examples/confidences/` - uncertain reasoning with confidence values
  * `Examples/exceptions/` - default rules with $block exceptions
  * `Examples/strategy/` - strategy files for proof search control

See `Examples/README.md` for a full guide with descriptions of every example.


Part 1: Questions and Answers
-----------------------------

GK answers questions by searching for proofs. Questions are marked
with `@question` in the JSON input.

### Example: Simple fact query

Create a file `test1.js`:

    [
      ["bird","tweety"],
      {"@question": ["bird","tweety"]}
    ]

Run it:

    ./gk test1.js

GK will find that "bird(tweety)" is directly given as a fact, producing
a proof with confidence 1.0 (certain).

### Example: Rule-based reasoning

Create a file `test2.js`:

    [
      ["bird","tweety"],
      [["bird","?:X"], "=>", ["flies","?:X"]],
      {"@question": ["flies","tweety"]}
    ]

Here `?:X` is a variable. The rule says "for all X, if bird(X) then flies(X)".
GK derives that tweety flies by applying the rule to the fact.

### Example: Finding answers with variables

Use the `$ans` predicate to collect variable bindings:

    [
      ["bird","tweety"],
      ["bird","polly"],
      ["fish","nemo"],
      {"@question": ["-bird","?:X"], "$ans": ["?:X"]}
    ]

GK will return multiple answers: tweety and polly.

Try these examples:

    ./gk Examples/core/grandfather.js         # rule-based inference
    ./gk Examples/core/algebra.js             # equality reasoning
    ./gk Examples/core/lists.js               # list operations
    ./gk Examples/core/negation.js            # negation


Part 2: Confidence Values
--------------------------

This section describes the confidence system presented in:
T. Tammet, D. Draheim, P. Jarv: "Confidences for commonsense reasoning",
CADE 2021. Comparison studies with ProbLog and Alchemy are at
https://logictools.org/confer/ (see also `study/` folder).

Real-world knowledge is uncertain. GK handles this with numeric
confidence values between 0 and 1.

### Specifying confidence

Attach a confidence to any statement with `@confidence`:

    [
      {"@logic": ["bird","tweety"], "@confidence": 0.9},
      {"@logic": [["bird","?:X"], "=>", ["flies","?:X"]], "@confidence": 0.8},
      {"@question": ["flies","tweety"]}
    ]

When GK derives a new fact from premises with confidences, the derived
confidence is the **minimum** of the premise confidences. Here "flies(tweety)"
gets confidence 0.8 (the minimum of 0.9 and 0.8).

Confidence values can be specified as:
  * Floats between 0.0 and 1.0: e.g., `0.85`
  * Integers between 2 and 100: treated as percentages, e.g., `85` means 0.85

### Positive and negative evidence

GK collects both positive evidence (proofs that something is true) and
negative evidence (proofs that something is false). The final confidence
for an answer is:

    final_confidence = positive_confidence - negative_confidence

For example, if there is evidence with confidence 0.8 that tweety flies
and evidence with confidence 0.3 that tweety does not fly, the final
confidence for "flies(tweety)" is 0.5.

### Cumulating evidence from multiple proofs

When GK finds multiple independent proofs for the same conclusion,
it cumulates their confidences. The cumulation formula with independence
coefficient `i` is:

    cumulated = old + new * (1 - old) * i

where `i` ranges from 0 (fully dependent proofs, no cumulation) to
1 (fully independent proofs, full cumulation). The default independence
is 0.5.

### Controlling confidence behavior

  * `-confidence <n>`: Set the minimum confidence threshold for answers
    (default 0.1). Answers below this are filtered out.
  * `-keepconfidence <n>`: Set the minimum confidence for keeping derived
    clauses during search (default 0, meaning keep all).
  * `-nocumulate`: Disable confidence cumulation across multiple proofs.
  * `-nonegative`: Do not collect negative evidence.

### Example: Competing evidence

    [
      {"@logic": ["safe","swimming"], "@confidence": 0.8},
      {"@logic": ["-safe","swimming"], "@confidence": 0.3},
      {"@question": ["safe","swimming"]}
    ]

GK reports positive confidence 0.8, negative confidence 0.3,
giving a final confidence of 0.5 for "safe(swimming)".

Try these examples:

    ./gk Examples/confidences/conf1.js        # positive + negative evidence
    ./gk Examples/confidences/cumulate.js      # cumulation from multiple proofs
    ./gk Examples/confidences/alarm.js         # burglary/alarm Bayesian problem
    ./gk Examples/confidences/smokes.js        # probabilistic smoking
    ./gk Examples/confidences/socialsmoking.js # social network propagation


Part 3: Default Rules and Exceptions
--------------------------------------

This section describes the default logic system presented in:
T. Tammet, D. Draheim, P. Jarv: "GK: implementing full first order
default logic for commonsense reasoning", IJCAR 2022.
ASP comparison examples are at https://logictools.org/gk/.

Default rules express what is typically true but may have exceptions.
The classic example: "birds typically fly, but penguins don't."

### The $block construct

Default rules use `$block` to mark exceptions:

    ["-bird","?:X"], ["flies","?:X"],
    ["$block", strength, ["$not", ["flies","?:X"]]]

The `$block` literal says: "this rule can be blocked if something
stronger says that X does not fly."

### Blocker strength

The first argument of `$block` encodes how strong/specific the default is.
A more specific rule (e.g., "penguins don't fly") overrides a more
general one (e.g., "birds fly"):

  * **Integer**: `0` = incomparable with all, `>0` = larger numbers are stronger
  * **Taxonomy reference**: `["$", "bird"]` or `["$", 42]` uses a class
    number from the WordNet taxonomy
  * **Combined**: `["$", "bird", 5]` uses taxonomy for comparison with
    other taxonomy-based blockers, and integer 5 for comparison with
    integer-only blockers

### Example: Birds fly, penguins don't

    [
      ["bird","tweety"],
      ["bird","pete"],
      ["penguin","pete"],
      [["penguin","?:X"], "=>", ["bird","?:X"]],

      {"@logic": [["-bird","?:X"],["flies","?:X"],
                   ["$block", 1, ["$not", ["flies","?:X"]]]]},

      {"@logic": [["-penguin","?:X"],["-flies","?:X"],
                   ["$block", 2, ["flies","?:X"]]]]},

      {"@question": ["flies","?:X"], "$ans": ["?:X"]}
    ]

The penguin rule (strength 2) overrides the bird rule (strength 1).
So tweety flies but pete does not.

### Using taxonomies with -defaults

Instead of manually assigning strength numbers, use the WordNet taxonomy
to automatically determine which concepts are more specific:

    ./gk myfile.js -defaults

This requires two files in the current directory (or in the `-datafolder` path):
  * `gk_name_number.txt`: maps words to taxonomy class numbers
  * `gk_taxonomy_packed.txt`: the packed taxonomy graph

With taxonomy-based strengths, you write:

    ["$block", ["$", "penguin"], ["$not", ["flies","?:X"]]]

and GK automatically knows that "penguin" is more specific than "bird"
because penguin is a subclass of bird in WordNet.

These files can be created using the utilities in the `Utils/` folder:

    cd Utils
    ./wngraph.py wn_graph.json
    ./taxonomy.py -p ../gk_taxonomy_packed.txt wn_graph.json
    ./name_sort_from_graph.py wn_graph.json > ../gk_name_number.txt

### How blocker checking works

GK's proof search has four phases, each getting roughly 1/4 of the
available time:

  1. **Find candidate proofs** for the question
  2. **Check blockers** on candidate proofs (try to prove blocking conditions)
  3. **Find negative evidence** (try to prove the negation of the answer)
  4. **Check blockers on negative proofs**

### Closure rules

To express closed-world assumptions (if something cannot be proved,
assume it is false), use closure rules:

    {"@logic": [["-p","?:X"], ["$block", 1, ["p","?:X"]]]}

This says: "not-p(X) holds by default, unless p(X) can be proved."

Try these examples:

    ./gk Examples/exceptions/trivial.js       # simplest default rule
    ./gk Examples/exceptions/bird_penguin.js   # birds fly, penguins don't
    ./gk Examples/exceptions/classify.js       # classification with defaults
    ./gk Examples/exceptions/nixon.js          # competing equal-strength defaults
    ./gk Examples/exceptions/hierarchy.js      # multi-level hierarchy

With taxonomy-based strengths:

    ./gk Examples/exceptions/taxonomy.js -defaults -datafolder Examples/exceptions


Part 4: Word Similarities (Experimental)
-----------------------------------------

GK can use word similarity scores to derive new facts by analogy.

Enable with:

    ./gk myfile.js -similarities

This reads `gk_similarity.txt` from the current directory (or `-datafolder`),
which contains lines like:

    cat dog 0.8
    car automobile 0.95

The similarity score (0 to 1) is used as a confidence modifier when
deriving facts by analogy.


Part 5: Shared Memory Knowledge Bases
---------------------------------------

For large knowledge bases, GK can load axioms into shared memory
and query them efficiently:

### Load a knowledge base

    ./gk axioms.js -readkb -mbsize 2000

This parses `axioms.js` and stores it in shared memory (2000 MB allocated).

### Query the knowledge base

    ./gk query.js -usekb

The query file contains only the question and any query-specific facts.
The shared memory KB provides the background axioms.

### Multiple databases

Use `-mbnr` to manage multiple simultaneous databases:

    ./gk kb1.js -readkb -mbnr 1001
    ./gk kb2.js -readkb -mbnr 1002
    ./gk query.js -usekb -mbnr 1001

### Save and reload databases

    ./gk axioms.js -readwritekb dump.bin
    ./gk -loadkb dump.bin

### Delete a database

    ./gk -deletekb
    ./gk -deletekb -mbnr 1001


Part 6: Search Structure and Output
-------------------------------------

### Non-successful results

When GK cannot find a definitive answer, it reports one of:

  * **"evidence below limit"**: proofs found but confidence too low
  * **"generic assumptions contradicted"**: question's assumptions lead
    to contradiction
  * **"no information"**: no relevant facts or rules found
  * **"no answers found"**: search completed without finding proofs
  * **"time limit, proof not found"**: ran out of time

### Controlling output verbosity

Use `-print <level>` to control output detail:

  * `1`: minimal output (answers only)
  * `10`: default (answers with proofs)
  * `15`: more detail
  * `20-60`: increasingly verbose debugging output
  * `100`: maximum verbosity

Use `-derived` to print all derived clauses (useful for debugging).

### Output formats

  * `-json`: JSON format output (default)
  * `-tptp`: TPTP format output (standard for theorem provers)


Part 7: Strategy Files
-----------------------

Strategy files control the proof search algorithm. They are JSON files
passed with `-strategy`:

    ./gk problem.js -strategy mystrategy.json

See `Doc/strategy_reference.md` for the complete strategy parameter reference.

### Default automatic strategy

When no strategy file is given, GK automatically selects a strategy
based on analysis of the input. The automatic strategy is likely to
be changed in future versions. Use `-print 13` to see the automatically
constructed strategy.

For typical commonsense problems (JSON-LD-LOGIC input, <= 1000 clauses),
the default is:

    {"strategy":["negative_pref"], "query_preference":1, "max_answers":10}

For larger clause sets (> 1000 clauses):

    {"strategy":["query_focus"], "query_preference":1, "max_answers":10}

The two main built-in strategies are:

  * `"negative_pref"`: binary resolution preferring negative literals
  * `"query_focus"`: goal-oriented set-of-support strategy

### Custom strategy example

    {
      "max_seconds": 10,
      "strategy": ["query_focus", "negative_pref"],
      "query_preference": 1,
      "max_answers": 5
    }

### Multiple sequential runs

A strategy file can specify multiple runs with different settings:

    {
      "runs": [
        {"max_seconds": 1, "strategy": ["unit"], "query_preference": 0},
        {"max_seconds": 5, "strategy": ["query_focus"], "query_preference": 1},
        {"max_seconds": 30, "strategy": ["negative_pref"], "query_preference": 2}
      ]
    }

Each run tries a different strategy. If an earlier run finds the answer,
later runs are skipped.

See `Examples/strategy/runs.txt` for a comprehensive example with 63 runs,
and `Examples/strategy/` for single-strategy examples.


Part 8: Large Knowledge Graphs
-------------------------------

GK can work with large commonsense knowledge graphs built from sources like
ConceptNet, Quasimodo, ATOMIC, WebChild, and others. Pre-built knowledge
graphs are available at https://logictools.org/gk/.

These are loaded as shared memory databases:

    ./gk multisource.js -readkb -defaults -mbsize 10000
    ./gk query.js -usekb

The `Utils/` folder contains tools for building knowledge bases from
various sources. See `Utils/README.md` for details on:

  * Building KBs from plain text (via relation extraction)
  * Filtering and converting Quasimodo data
  * Creating WordNet taxonomy files
  * Generating default logic KBs with taxonomies


Part 9: Input Format
---------------------

GK uses JSON-LD-LOGIC format (files with `.js` extension):

    [
      {"@logic": ["bird","tweety"], "@confidence": 0.9},
      {"@logic": [["bird","?:X"], "=>", ["flies","?:X"]]},
      {"@question": ["flies","tweety"]}
    ]

See `Doc/json_ld_logic.md` for the complete specification.


Further Reading
---------------

  * `Examples/README.md` - Examples guide organized by category (core, confidences, exceptions)
  * `demo/README.md` - Commonsense reasoning examples with confidences and defaults
  * `Doc/json_ld_logic.md` - JSON-LD-LOGIC input format specification
  * `Doc/cli_reference.md` - Complete command-line reference
  * `Doc/strategy_reference.md` - Strategy file parameter reference
  * `ARCHITECTURE.md` - System architecture and module overview
  * https://logictools.org/gk/ - Online documentation and downloads
  * https://logictools.org/gk/tutorial.html - Online tutorial
