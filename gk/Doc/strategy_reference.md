Strategy File Reference
=======================

Strategy files are JSON files that control GK's proof search algorithm.
Pass them with `-strategy <filename>` or `-strategytext '<json>'`.

Example:

    {
      "max_seconds": 10,
      "strategy": ["query_focus", "negative_pref"],
      "query_preference": 1,
      "max_answers": 5
    }


Timeout Parameters
------------------

    max_seconds (integer)
        Maximum runtime for this strategy run in seconds.

    total_seconds (integer)
        Total cumulative timeout across all runs.

    max_dseconds (integer)
        Maximum runtime in deciseconds (tenths of seconds).
        When < 20, triggers strong unit cutoff optimization.


Answer Limits
-------------

    max_answers (integer, default: unlimited)
        Stop after finding this many answers.


Strategy Selection
------------------

    strategy (string or array of strings)
        Selects the resolution/derivation strategy. Can be a single
        strategy name or an array combining multiple strategies.

Available strategy names:

    negative_pref
        Prefer negative clauses in resolution. Good general-purpose
        strategy, used as default.

    positive_pref
        Prefer positive clauses in resolution.

    query_focus
        Focus search on goal/query clauses. Good for query answering.

    hyper
        Use hyperresolution (resolve multiple literals at once).

    unit
        Restrict to unit resolution (only resolve with single-literal
        clauses). Fast but incomplete.

    pure_unit
        Strict unit resolution without paramodulation on longer clauses.

    double
        Allow resolution arguments up to length 2.

    triple
        Allow resolution arguments up to length 3.

    hardness_pref
        Prefer clauses with lower computational hardness.

    knuthbendix_pref
        Use Knuth-Bendix term ordering preference. Useful for
        equational reasoning.

    prohibit_nested_para
        Prevent nested paramodulation steps.

    posunitpara
        Restrict paramodulation to positive unit clauses.

    max_ground_weight
        Use maximum ground weight ordering.

Combining strategies:

    "strategy": ["query_focus", "positive_pref"]


Clause Selection and Queue Control
------------------------------------

    query_preference (integer, 0-4)
        Controls how clauses are partitioned into selection queues:

        0  Single queue for all clauses
        1  Exactly as marked by roles (goal/assumption/axiom)
        2  Non-included axioms become assumptions; positive goals
           become assumptions
        3  Only fully negative goal clauses stay as goals; rest
           become axioms
        4  All clauses treated as axioms regardless of role

    given_queue_ratio (integer, 1+)
        Ratio for selecting from different clause queues.
        Alias: weight_select_ratio.

    reverse_clauselist (integer, 0 or 1)
        Reverse initial clause list without sorting (for non-query
        problems).


Clause Roles and Strategy
-------------------------

Each input clause carries a role assigned via the `@role` key (or
inferred from `@question`). The role influences the proof search
only through queue placement in the given-clause loop:

  * **Goal roles** (`conjecture`, `negated_conjecture`, `question`)
    → GOAL queue
  * **Assumption roles** (`assumption`, `hypothesis`)
    → ASSUMPTIONS queue
  * **Axiom roles** (`axiom`, `extaxiom`)
    → AXIOMS queue
  * **Derived clauses** with mixed parents → a mixed queue matching
    the highest-priority parent class.

Whether these queues are actually kept separate depends on
`query_preference`:

    0   All clauses share one queue; role is only a label.
    1   Queues are kept separate exactly as marked by roles.
    2   Positive goal units are demoted to assumptions;
        non-included axioms are promoted to assumptions.
    3   Only fully negative goal clauses stay as goals; assumptions
        are demoted to axioms.
    4   Every clause is forced to axiom; role is ignored entirely.

The named strategy `query_focus` is the one that actually exploits
role-based queue separation — it prefers GOAL-queue clauses during
given-clause selection. `negative_pref`, `positive_pref`, and
`hardness_pref` use orthogonal preferences and do not key off role
directly.


Role Semantics (Bottom Line)
----------------------------

A short summary of how `@role` and `@question` interact at parse
time (the full discussion is in `Doc/json_ld_logic.md`):

  * `@question` and `@role` are **mutually exclusive** in the same
    object — this is enforced by the parser, not a convention.
  * `@question` is macro-expanded to `@role: "question"` plus
    `@logic: <formula>`.
  * `@role: "question"` is internally rewritten to
    `negated_conjecture`: the formula is negated automatically, and
    free variables are wrapped in `$ans(...)` for answer collection.
  * `conjecture` and `negated_conjecture` share one internal role
    number; they differ only in whether the parser negates the
    formula (`conjecture` is negated, `negated_conjecture` is taken
    as-is).
  * `hypothesis` and `assumption` are indistinguishable internally.
  * Role affects search **only** when the active strategy reads
    queue position — i.e. `query_focus`, or any non-zero
    `query_preference`.


axiom vs extaxiom
-----------------

`extaxiom` is an "imported / background axiom" marker. A clause gets
extaxiom role in two ways:

  * explicit `@role: "extaxiom"`; or
  * `@role: "axiom"` (or no role) when the clause comes from an
    included file — the parser prefixes its `@name` with `$inc_` and
    auto-upgrades the role. In practice this happens for clauses
    loaded via the shared-memory KB (`-readkb` / `-usekb`), not for
    a plain `./gk file.js` run.

The two roles share storage, weighting, indexing, SINE filtering,
and confidence handling. They also collapse to the same derived-
clause role (`FROMAXIOM`) after the first inference — the extaxiom
marker does not propagate to children.

The **one behavioural difference** during search is in initial
clause activation under `query_preference: 2`:

  * normal `axiom` clauses are suppressed from initial activation
    (they are pushed back into the regular selection queue);
  * `extaxiom` clauses are always initially activated.

This is the "trust the background library more than the problem
axioms" hook: when a large imported KB is available and
`query_preference: 2` is in effect, the library's clauses are
activated immediately while the problem's own axioms are held back.
Under `query_preference` 0, 1, 3, or 4 there is no behavioural
difference between the two roles.

Proof output preserves the label (`axiom` vs `extaxiom`), so the
distinction remains useful for provenance even when it has no
operational effect.


Clause Size and Complexity Limits
----------------------------------

These limits control which derived clauses are kept. Setting a value
to 0 means no limit for that dimension.

    max_size (integer, 0+)
        Maximum number of literals in a kept clause.

    max_depth (integer, 0+)
        Maximum term nesting depth in a kept clause.

    max_length (integer, 0+)
        Maximum arity/length of terms in a kept clause.

    max_weight (integer, 0+)
        Maximum total weight of a kept clause.


Clause Weighting
-----------------

These parameters control how clause weight is calculated, affecting
which clauses are selected first.

    depth_penalty (integer)
        Weight penalty per unit of term depth.

    length_penalty (integer)
        Weight penalty per unit of term length.

    var_weight (integer)
        Weight assigned to each variable occurrence.

    repeat_var_weight (integer)
        Additional weight for repeated variable occurrences.


Equality and Rewriting
-----------------------

    equality (integer, 0 or 1)
        Enable equality reasoning (paramodulation). Default depends
        on whether the problem contains equalities.

    rewrite (integer, 0 or 1)
        Enable term rewriting using oriented equalities.


Advanced Search Methods
------------------------

    instgen (integer, 0 or 1)
        Use instantiation-based generation method.

    propgen (integer, 0 or 1)
        Use propositional generation with SAT solver integration.


SINE Filtering
--------------

SINE (Sufficent axiom Inclusiveness for Natural Efficiency) filters
axioms by relevance to the goal, useful for large axiom sets.

    sine (integer, 0-2)

        0  No SINE filtering (use all axioms)
        1  Weak SINE filtering
        2  Strong SINE filtering


Confidence Parameters
---------------------

    independence (integer, 0-100)
        Independence coefficient for confidence cumulation, as a
        percentage. 0 = fully dependent (no cumulation),
        100 = fully independent (full cumulation). Default: 50.

    keepconfidence (integer, 0-100)
        Minimum confidence threshold for keeping derived clauses,
        as a percentage.

    cumulate_method (integer, 0-10)
        Method for combining confidence values:
        0  Use independence only, not ratios
        1  List membership percentage
        2  Probabilities ratio
        3+ Experimental methods


Output Control
--------------

    print (integer, 0 or 1)
        Enable basic printout.

    print_level (integer, 0+)
        Verbosity level (higher = more output). Default: 15.

    print_json (integer, 0 or 1)
        Output in JSON format.

    print_tptp (integer, 0 or 1)
        Output in TPTP format.


Multiple Runs
-------------

The `runs` key specifies an array of strategy configurations to try
sequentially. Each run is independent with its own timeout and parameters.
If an earlier run finds the answer, later runs are skipped.

    {
      "runs": [
        {"max_seconds": 1, "strategy": ["unit"], "query_preference": 0},
        {"max_seconds": 5, "strategy": ["query_focus"], "query_preference": 1},
        {"max_seconds": 30, "strategy": ["negative_pref"], "query_preference": 2}
      ]
    }

Parameters at the top level apply to all runs as defaults, unless
overridden within a specific run.

See `Examples/runs.txt` for a comprehensive real-world example with
63 sequential runs combining different strategies, query preferences,
and depth limits. Use it with:

    ./gk problem.txt -strategy Examples/runs.txt


Default Strategy
-----------------

When no strategy file is specified, GK automatically selects a strategy
based on analysis of the input clauses. The automatic strategy is likely
to be changed in future versions. Use `-print 13` to see the
automatically constructed strategy.

For **JSON-LD-LOGIC input** (the typical gk case), the automatic
strategy is:

  * `max_answers`: 10 (or 1 if `-firstanswer` is set)
  * `independence`: 100
  * `max_seconds`: value of `-seconds` flag (default 10)
  * Strategy selection based on clause count:
    - **> 1000 clauses**: `"strategy": ["query_focus"], "query_preference": 1`
    - **<= 1000 clauses**: `"strategy": ["negative_pref"], "query_preference": 1`

For **TPTP input** (classical theorem proving), the automatic strategy
uses `negative_pref` with no clause size limits and constructs a
multi-run strategy trying various combinations of strategies,
queue ratios, and clause limits.

If the automatic strategy is not used (e.g., when a strategy file is
given but contains no strategy key), the hardcoded fallback is:

    {
      "print": 1,
      "print_level": 15,
      "strategy": "negative_pref"
    }


Tips
----

  * For small problems: `"strategy": ["unit"]` is fast but incomplete
  * For query answering: `"strategy": ["query_focus"]` with
    `"query_preference": 1`
  * For equational reasoning: add `"equality": 1` and
    `"strategy": ["knuthbendix_pref"]`
  * For large knowledge bases: use SINE filtering with `"sine": 1` or `2`
  * For finding multiple answers: set `"max_answers": 10` and increase
    `"max_seconds"`
  * For confidence problems: adjust `"independence"` based on how
    independent your evidence sources are
