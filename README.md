nlpsolver
=========

Nlpsolver is an experimental system for automated reasoning in natural language,
capable of performing both natural language inference (NLI) and question answering.
It contains two independent pipelines:

* **llmpipe** — the newer LLM-based pipeline (GPT, Claude, Gemini) that replaces the Stanza
  parser with a two-stage LLM semantic parser. See the `llmpipe/` folder and its README.

* **udppipe** — the older Stanza/UD-based semantic parser pipeline, described in the paper
  [An Experimental Pipeline for Automated Reasoning in Natural Language](https://link.springer.com/chapter/10.1007/978-3-031-38499-8_29).
  Does not use LLMs. See the `udppipe/` folder and its README.

Both pipelines share the same `gk` theorem prover backend and have a similar core logic representation.

Each pipeline contains:
* A semantic parser from English to extended first order logic.
* A first-order logic commonsense reasoner solving the problem expressed in extended logic.
* A subsystem for converting the proof given by the reasoner to English.

The commonsense reasoner is built on top of
a [high-performance FOL reasoner](https://link.springer.com/chapter/10.1007/978-3-030-29436-6_32),
extended to use [numeric confidences](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_29)
and [defeasible rules](https://link.springer.com/chapter/10.1007/978-3-031-10769-6_18).

Nlpsolver is developed with a goal to be (a) a backbone of our research in
combining machine learning and large language models with logic-based
symbolic reasoning, (b) using automated reasoner as an interface
between natural language and external tools like database systems and scientific
calculations.

Subfolders
------------

* llmpipe: the llm-based pipeline, needs secrets and gk folders.
* udppipe: the Stanza/UD-based pipeline, needs the gk folder.
* secrets: empty folder for files with LLM api secrets.
* gk: the gk commonsense reasoner used in both pipelines
* exparchive: archive of data from experiments
* amr: standalone experimental amr-based parser


Installation
------------

The system requires Linux and has been developed using Python 3.8 and later.

**For udppipe**, the external dependencies are:
* The Stanford Stanza NLP package https://stanfordnlp.github.io/stanza/
    converting English to a [UD](https://universaldependencies.org/) graph.
* The reasoner binary `gk`, included in the system.
* Data files from the tarball http://logictools.org/data/nlpsolver_data.tar.gz

**For llmpipe**, the only external dependency beyond Python is:
* The reasoner binary `gk` and its data files (same tarball as above).
* An API key for at least one LLM provider (GPT, Claude, Gemini or Deepseek) in `secrets`

The subfolders `gui` and `amr` contain experimental code in development, and
are not currently used by either pipeline.

The installation and use of both pipelines is described in the corresponding separate READMEs.






