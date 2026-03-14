gk
==

GK is a commonsense reasoning system.

The main developer is Tanel Tammet (tanel.tammet@gmail.com), 
with contributions by Priit Järv (priit.jarv@gmail.com).

It is built upon the gkc (gk core) at https://github.com/tammet/gkc by Tanel Tammet 
(see the paper [high-performance FOL reasoner](https://link.springer.com/chapter/10.1007/978-3-030-29436-6_32))
and a modified version of the whitedb database http://whitedb.org by Tanel Tammet and Priit Järv.

GK extends GKC to use [numeric confidences](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_29)
and [defeasible rules](https://link.springer.com/chapter/10.1007/978-3-031-10769-6_18).


Running
-------

Simplest way to run:

    ./gk problem_file_name

Example:

    ./gk dstudy/d1.js

GK can parse and prepare a large axiom file into a shared memory database to perform quick
independent queries upon this pre-built base. Several shared memory databases may be present
at the same time: use different memory database numbers for indicating which to load or use.
The memory database can be dumped to a disk for quick loading later. 

The following is a list of available commands as output by `./gk -help`:

    basic proof search with an automatic strategy for JSON-LD-LOGIC format input:
    gk <filename> 

    options for proof search with a user-determined strategy:
    -strategy <strategy file>
        use the json <strategy file> to determine proof search strategy and options
    -strategytext 'strategy text in json' 
        alternatively input strategy text directly from command line

    options and parameters for using the shared memory database of axioms:
    -usekb
        use the axioms in the shared memory database in addition to other input
    -mbnr <shared memory database nr>
        if omitted, number 1000 is used
    gkc -readkb <logic file>
        parse and load a logic file into the shared memory database
    gkc -deletekb
        delete the present shared memory database (not necessary for reading a new one)

    options with numeric parameters:
    -seconds <n>
        use <n> as an upper limit of running time in seconds;
    -mbsize <megabytes to allocate initially>
        if omitted, 5000 megabytes assumed
    -print <nr>
        indicate the amount of output: 10 is default, bigger numbers give more

    options without parameters:
    -defaults
        starts using a taxonomy for comparing defaults, for this
        reads in name/number file with this name: gk_name_number.txt
        reads in packed graph file with this name: gk_taxonomy_packed.txt
    -nonegative
        if present, do not collect negative evidence
    -firstanswer
        do not attempt to find multiple derivations and answers
    -version
        show confer version
    -help
        show this help text;
        
See 

* http://logictools.org/confer/ for some details and examples.
* https://logictools.org/gk/ for more details and examples, including
  the https://logictools.org/gk/tutorial.html


Datasets
--------

These datasets GK uses for taxonomy reasoning are built from the hypernym and hyponym
 relations of Wordnet:

* gk_name_number.txt : a mapping of Wordnet synsets to class numbers
* gk_taxonomy_packed.txt : packed topologically sorted class taxonomies 

Using defaults
--------------

First, see and run the examples in the dstudy folder.

The defaults are encoded like this:

    {
      "@logic": [["-bird","?:X"],["flies","?:X"], 
                ["$block", ["$","bird"], ["$not", ["flies", "?:X"]]]]
    }

where the first blocker argument above

    ["$","bird"] 

encodes the strength/specificity of the default. Here the "bird"
is meant for being replaced automatically with the class number via
using the -defaults key as shown next.

The first blocker argument can have following alternative forms:

    * integer: 
       if 0, no blockers are stronger or weaker than this.
       if >0, larger number is considered stronger/more specific
    * ["$",integer] where integer is a class number in the taxonomy
    * ["$",string] where string is converted to a class number in the taxonomy
    * ["$",integer/string,integer2] where
        integer/string is like in the previous case, class number or word
        integer2 encodes strength directly like in the first case

        When comparing this form with the first single integer form above,
        the integer2 is used for comparison and integer/string is ignored.

        When comparing two blockers of this/last form, the integer2 of
        both is used for comparison in case the integer/string2 is 
        mutually incomparable (no one blocks another)

Blockers with equal first arguments block each other mutually, unless
their strength integer is 0.       

Next, use the wordnet taxonomies for comparing defaults:

    ./gk d5a.js -defaults

which assumes the files gk_name_number.txt and gk_taxonomy_packed.txt
are in the current folder. The first of these is used for automatically
replacing words in the blocker first argument term with the class number
from the graph. It can be created by the name_sort_from_graph.py utility
in the Utils folder. The Utils folder is otherwise mostly a copy of 
Priit's triplestore subfolder.

Next, create a shared memory kb and use it for queries:

    ./gk d5a_kb.js -readkb -defaults
    ./gk d5a_q.js -usekb

It is also OK to use the -defaults switch in the last command above.












