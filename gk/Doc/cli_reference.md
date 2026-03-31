GK Command-Line Reference
=========================

Usage:

    gk [options] <filename1> [<filename2> ...]
    gk -readkb <filename> [options]
    gk -usekb [options] [<query_file>]
    gk -help


Input Files
-----------

GK accepts one or more input files in JSON-LD-LOGIC format
(`.js` extension). See `Doc/json_ld_logic.md` for the format
specification.


Primary Commands
-----------------

These are mutually exclusive. If none is specified, `-prove` is assumed.

    -prove
        Prove the goals in the input (default behavior).

    -readkb <filename>
        Parse a logic file and load it into a shared memory database.
        Typically used with -mbsize to allocate sufficient memory
        (at least 100 MB, recommended 1000+ MB).

    -usekb
        Use the shared memory database as background axioms in addition
        to the input file. Cannot be combined with -datafolder,
        -defaults, -similarities, or -relatedwords.

    -writekb <filename>
        Write the current shared memory database to a file on disk.

    -loadkb <filename>
        Load a previously saved database from disk into shared memory.

    -readwritekb <datafile> <dumpfile>
        Parse a data file and write the resulting database to a dump file.
        Requires at least 100 MB via -mbsize.

    -deletekb
        Delete the current shared memory database. Linux and macOS only.

    -help, --help
        Display the help text.

    -version, --version
        Display the gk version.

    -licence
        Display license information.


Numeric Parameters
------------------

    -seconds <n>
        Maximum running time in seconds. Default: 10.

    -mbsize <megabytes>
        Memory to allocate for the database. Default: 5000 MB.
        Minimum: 10 MB. For -readkb, use at least 1000 MB.

    -mbnr <number>
        Shared memory database number, allowing multiple databases
        to coexist. Default: 1000. Minimum: 10.

    -parallel <n>
        Number of parallel search threads. Default: 1.

    -print <level>
        Output verbosity level. Default: 10.
          1      Minimal (answers only)
          10     Default (answers with proofs)
          15     More detail
          20-60  Increasingly verbose debug output
          100    Maximum verbosity

    -confidence <n>
        Minimum confidence threshold for reported answers.
        Default: 0.1. Answers with confidence below this are filtered out.
        Accepts float 0-1 or integer 2-100 (as percentage).

    -keepconfidence <n>
        Minimum confidence for keeping derived clauses during search.
        Default: 0 (keep all). Accepts float 0-1 or integer 2-100.


String Parameters
-----------------

    -strategy <filename>
        JSON strategy file controlling proof search. See
        Doc/strategy_reference.md for the complete parameter reference.

    -strategytext '<json>'
        Strategy specified directly as a JSON string on the command line.

    -text '<logic text>'
        Input logic in simple/Otter format directly from the command line.

    -jstext '<json text>'
        Input logic in JSON-LD-LOGIC format directly from the command line.

    -datafolder <path>
        Folder containing auxiliary data files (gk_name_number.txt,
        gk_taxonomy_packed.txt, gk_similarity.txt, gk_relatedwords.txt).
        If not specified, these are looked for in the current directory.

    -task <name>
        Run a specific auxiliary task.


Boolean Flags
-------------

### Output control

    -json
        Output in JSON format. This is the default.

    -tptp
        Output in TPTP format (standard theorem prover format).
        Cannot be combined with -json.

    -derived
        Print all derived clauses, regardless of -print level.
        Useful for debugging.

### Search control

    -firstanswer
        Stop after finding the first answer. Do not search for
        multiple derivations or alternative answers.

    -nonegative
        Do not collect negative evidence. Only positive proofs
        are considered.

    -nocheck
        Do not check blockers. Default rules are applied without
        checking for exceptions.

    -nocumulate
        Do not cumulate confidences across multiple proofs.
        Each proof is reported independently.

    -nosimilarities
        Disable similarity-based derivation even if similarity
        data has been loaded (useful with -usekb).

### Data loading

    -defaults
        Load and use the WordNet taxonomy for comparing default rule
        strengths. Reads two files from the current directory
        (or -datafolder path):
          gk_name_number.txt       word-to-class-number mapping
          gk_taxonomy_packed.txt   packed taxonomy hierarchy

    -similarities, -similarity
        Load and use word similarity data. Reads:
          gk_similarity.txt

    -relatedwords
        Load and use related words data. Reads:
          gk_relatedwords.txt

### Format conversion

    -convert
        Convert input between formats.

    -clausify
        Convert input to clausal normal form. Cannot be combined
        with -usekb.


Auxiliary Data Files
--------------------

When using `-defaults`, `-similarities`, or `-relatedwords`, GK looks for
these files in the current directory or the `-datafolder` path:

    gk_name_number.txt
        Maps words to taxonomy class numbers. Created by
        Utils/name_sort_from_graph.py.

    gk_taxonomy_packed.txt
        Packed WordNet taxonomy hierarchy. Created by
        Utils/taxonomy.py -p.

    gk_similarity.txt
        Word similarity scores, one per line:
          word1 word2 score
        where score is 0.0 to 1.0.

    gk_relatedwords.txt
        Related word associations.


Usage Examples
--------------

### Basic proof search

    ./gk problem.js
    ./gk problem.js -seconds 30 -print 15

### With confidence and defaults

    ./gk problem.js -defaults -confidence 0.2

### Shared memory knowledge base

    ./gk axioms.js -readkb -mbsize 2000 -defaults
    ./gk query.js -usekb
    ./gk query.js -usekb -mbnr 1001
    ./gk -deletekb

### Strategy file

    ./gk problem.js -strategy mystrategy.json -seconds 60

### Direct input from command line

    ./gk -jstext '[["bird","tweety"], {"@question": ["bird","tweety"]}]'

### Multiple input files

    ./gk facts.js rules.js query.js
