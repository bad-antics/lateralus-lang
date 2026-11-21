# Fast String Edits with `stdlib/rope.ltl`

Naive string concatenation in a loop is O(n²) — every `s = s + chunk`
copies the whole prefix. A **rope** keeps text in a binary tree of leaves
so `concat`, `split`, `insert`, and `delete` cost O(log n) pointer work
instead of O(n) copying.

This tutorial walks the full API. Companion: `examples/rope_tutorial.ltl`.

---

## The model

Each node is a map:

- `leaf`: `{kind:"leaf", text, len}` — an immutable chunk of text
  (leaves longer than 64 chars are split by `rebalance`)
- `branch`: `{kind:"branch", left, right, len, weight}` — `weight` is
  the total length of the left subtree, which is what lets `split_at`
  descend in O(log n) instead of scanning

## Operations

- `from_str(s)` — build a rope (auto-rebalances long inputs)
- `concat(a, b)` — O(1) join; empty sides short-circuit
- `index(n, i)` / `substr(n, i, j)` — random access via an explicit
  stack walk
- `split_at(n, i)` — returns `[left, right]`
- `insert(n, i, s)` / `delete(n, i, count)` — split, splice, concat
- `length`, `to_str`, `rebalance`

## One runtime quirk the tutorial works around

`index()` ends with `char_at(n["text"], i)`, but `char_at` is **not a
runtime builtin** — the generated Python raises `NameError`. The
inlined copy uses `slice(t, i, i + 1)`, which returns the same
single-character string. Module bug flagged for a fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/rope_tutorial.ltl
python -m lateralus_lang check examples/rope_tutorial.ltl
python -m pytest tests/test_rope_tutorial.py -x -q
```
