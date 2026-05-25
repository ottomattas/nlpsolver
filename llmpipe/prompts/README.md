# prompts/

LLM system prompts used by the two-stage parser (`solver/llmparse.py`).
Stage 1 converts English text into a JSON list of "Atomic Semantic
Units" (ASUs); Stage 2 converts that ASU JSON into the predicate-logic
JSON that the rest of the pipeline clausifies and feeds to the prover.

## Files

Each stage uses three files, all loaded once per process and cached:

| File | Role |
|------|------|
| `stage1_instructions_full.txt` | Stage-1 specification (entity IDs, ASU types, scope/quantifier rules, modal-mode table, etc.) |
| `stage1_examples.txt`          | Worked Stage-1 examples (English → ASU JSON) |
| `stage1_checklist_full.txt`    | Short procedural checklist appended at the very end |
| `stage2_instructions_full.txt` | Stage-2 specification (predicate inventory, quantifier mapping per ASU type, modal classifiers, $defq encoding) |
| `stage2_examples.txt`          | Worked Stage-2 examples (ASU JSON → logic JSON) |
| `stage2_checklist_full.txt`    | Short procedural checklist appended at the very end |

The checklists are kept separate so the most error-prone rules can be
re-emphasised at the bottom of the prompt without bloating the main
instructions.

## How a system prompt is assembled

`solver/llmparse.py::_compose_prompt` concatenates the three files in
this order (with a single fixed separator between instructions and
examples, and a blank line before the checklist):

```
<instructions_full.txt>

Examples:

<examples.txt>

<checklist_full.txt>
```

The resulting string becomes the `system` prompt sent to the LLM.  The
`user` prompt is just the input text (Stage 1) or the Stage-1 JSON
(Stage 2).  See `_compose_prompt` and `parse_text` in
`solver/llmparse.py` for the exact wiring.
