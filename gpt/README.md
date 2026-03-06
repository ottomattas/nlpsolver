Experiments with using GPT for supporting semantic parsing
==========================================================

This folder contains a small program for performing GPT api calls from a command line

    gpt.py

and several experimental system prompts for various tasks in the `prompts/` subfolder,
including

* prompts/logifyprompt3.txt : a large multishot prompt converting English to logic
* prompts/simplelogify.txt : a naive zero-shot prompt converting English to logic
* prompts/simplifyprompt1.txt : a naive zero-shot prompt for simplifying NL text
* prompts/simplifyprompt3.txt : an improved zero-shot prompt for simplifying NL text
* prompts/genprompt5.txt : a multishot prompt for determining suitable quantification
* prompts/coreferenceprompt1.txt : a multishot prompt for solving coreference tasks

Additionally we provide several regression tests as python files in the `tests/` subfolder,
containing a list of problems with expected answers:

* tests/llm_core_test.py : LLM-oriented subset/modification of the core_test.py
* tests/core_test.py : core regression test problems for the pipeline
* tests/llm_allen_test.py : LLM-oriented subset of the allen_test.py
* tests/allen_test.py : regression tests inspired by the Allen AI Proofwriter
* tests/hans_test.py : a representative sample of problems from the HANS test set
* tests/tests_wikipedia.py : a test set built from 10 typical Wikipedia articles
  tests/tests_wikipedia_source.py : a commented file from which the test set above is built

Direct reasoning results of running GPT4 (gpt-4o-2024-05-13) and GPT3.5 (gpt-3.5-turbo-0125)
are in the `results/` subfolder:

* results/llm4_core_test_results.txt : GPT4 results on the test set llm_core_test.py
* results/llm3_core_test_results.txt : GPT3.5 results on the test set llm_core_test.py
* results/llm4_allen_test_results.txt : GPT4 results on the test set llm_allen_test.py
* results/llm3_allen_test_results.txt : GPT3.5 results on the test set llm_allen_test.py
* results/llm4_hans_test_results.txt : GPT4 results on the test set hans_test.py
* results/llm3_hans_test_results.txt : GPT3.5 results on the test set hans_test.py

Parsing results of running GPT4 (gpt-4o-2024-05-13) as a parser on the same regression tests,
plus programmatically fixing the json and running the reasoner on the fixed versions.
The following small program is used for fixing (input/output should be set at the
initial part of the program):

    nlpconvcollected.py

* results/llm_tests_core1_results.txt - GPT4 raw parsing results on llm_core_test.py
* results/llm_tests_core1_results_converted.py - programmatically fixed json version of the parsing results above
* results/llm_tests_core1_parsed_solved_results.txt - reasoning results on the fixed version above

* results/llm_tests_allen_results.txt - GPT4 raw parsing results on llm_allen_test.py
* results/llm_tests_allen_results_converted.py - programmatically fixed json version of the parsing results above
* results/llm_tests_allen_parsed_solved_results.txt - reasoning results on the fixed version above

* results/llm_tests_hans_results.txt - GPT4 raw parsing results on hans_test.py
* results/llm_tests_hans_results_converted.py - programmatically fixed json version of the parsing results above
* results/llm_tests_hans_parsed_solved_results.txt - reasoning results on the fixed version above

NB! The file prompts/logifyprompt3.txt does not generate exactly the same representation
as nlpsolver uses. Instead, it uses a somewhat simpler and more abstract format,
which is quite similar to the one used by nlpsolver and should be convertable
relatively easily.

Before running gpt.py you have to create a file

    gpt_secrets.js

in this folder (already present for authorised users), containing just

    {"gpt_key": "put your GPT api key here"}

Similarly, `claude_secrets.js` and `gemini_secrets.js` hold keys for those providers.

Then try out

    ./gpt.py 4 -s prompts/logifyprompt3.txt "Elephants are big. John is an elephant."

and then run ./gpt.py without arguments to see available keys and options.
