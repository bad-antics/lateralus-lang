# Multi-Pattern Search with `stdlib/aho_corasick.ltl`

Aho-Corasick finds *all* pattern occurrences in one linear pass — the
algorithm behind grep, virus scanners, and NLP tokenizers. Build the
goto/fail/output automaton once, then stream any text.

This tutorial exercises build, find_all, find_all_starts, and
contains_any. Companion: `examples/aho_corasick_tutorial.ltl`.

---

## How it works

- **Trie:** each node's `goto` maps byte→child; `output` lists pattern
  ids ending there
- **Fail pointers:** BFS computes the longest proper-suffix fallback,
  merging outputs so suffix matches surface for free
- `find_all` → `[pattern_id, end_pos)`; `find_all_starts` converts to
  start positions; `contains_any` early-exits

## Verified on the classic example

Patterns `["he","she","his","hers"]` on `"ushers"` → she@1, he@2,
hers@2 — overlapping and suffix matches all found in one pass.

## Bug found while building the tutorial

`char_at()` is not a runtime builtin (`NameError`) — used at all three
scan sites. Inlined copy uses `slice(i, i+1)`. Flagged for a module
fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/aho_corasick_tutorial.ltl
python -m lateralus_lang check examples/aho_corasick_tutorial.ltl
python -m pytest tests/test_aho_corasick_tutorial.py -x -q
```
