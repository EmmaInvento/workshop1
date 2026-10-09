# Prompt changelog

## Workshop 3 conversation prompt

### `municipal_assistant_v6.txt` — Multi-turn extension

- Prompt: `municipal_assistant_v6.txt`
- Model: not evaluated live for this version
- Test set: `workshop-2-golden` is available for single-request regression checks. Version:    RGF0YXNldFZlcnNpb246Nw==
- Result: not measured; the v5 result above does not apply to v6
- Change: extends the original Workshop 3 multi-turn prompt with conversation history,
  later corrections, and explicit behavior when older turns have been removed; retains
  the four-field JSON output contract
- Rationale: keep the upstream single-turn v5 intact while making the Workshop 3
  conversation prompt the default