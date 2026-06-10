# Running nlpsolver on macOS (Apple Silicon)

Verified working on macOS ARM64 (June 2026): the `llmpipe` pipeline reproduces
the published Linux baseline on the 100-subset (98-100% per model, see
`results/parsing-architecture/results.md` §6).

## Setup

1. **Clone — no gk steps needed.** The repo ships two prover binaries:
   `gk/gk` (Linux x86-64, the canonical path) and `gk/gk-macos-arm64`
   (extracted from `gk/gk-macos-ARM64.zip`). On Apple Silicon the pipeline
   selects the ARM64 build automatically (`llmpipe/solver/globals.py`,
   `prover_fname` selection). Do NOT overwrite `gk/gk` with the mac binary —
   that path stays Linux for upstream compatibility.

2. **API keys.** Create plain-text key files (gitignored) in `secrets/`:

       secrets/gpt_secrets.txt
       secrets/claude_secrets.txt
       secrets/gemini_secrets.txt
       secrets/deepseek_secrets.txt

   Each file contains just the provider API key. See `secrets/README.txt`.

3. **Python.** Stock python3, standard library only — no pip installs needed.

## Smoke test

    # prover alone
    ./gk/gk-macos-arm64 gk/Examples/core/grandfather.js

    # full pipeline (one cheap LLM call; responses are cached in llmpipe/cache.db)
    cd llmpipe/solver
    python3 solve.py "Elephants are big. John is an elephant. Who is big?" -llm gemini

Expected answer: `John.`

## Notes

- LLM response caching is ON by default (keyed on provider/version/params/
  prompt). Never use `-nollmcache` for batch runs — project convention.
- If you ever obtain a gk binary outside of git (browser download), macOS
  quarantine may block it: `xattr -d com.apple.quarantine <file>`. Binaries
  extracted from the committed zip via git are not quarantined.
- Batch runs: `cd llmpipe && python3 runtests.py tests/tests_core_100.py`
  (output under the gitignored `llmpipe/testresults/`).
