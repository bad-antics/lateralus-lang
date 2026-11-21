# Compressed Integer Sets with `stdlib/roaring.ltl`

Roaring bitmaps power Lucene, ClickHouse, and Druid: 32-bit ints split
into a 16-bit container key + 16-bit value, with each container stored
as a sorted array (≤4096 entries) or a 64Kbit bitmap — memory-efficient
*and* fast for both sparse and dense sets.

`stdlib/roaring.ltl` implements the core: `add`, `has`, `cardinality`,
`union`, `to_list`. Companion: `examples/roaring_tutorial.ltl`.

---

## Model

- `containers`: map of `hi16 → container`
- Array container: sorted `values` list + `card`
- Bitmap container: 1024 u64 words + `card`
- `add` promotes array→bitmap past 4096 entries in one container
- `union` re-adds all elements (simple, correct — not the optimized
  container-merge real Roaring uses)

## Verified behavior

- Values across hi16 boundaries (`1`, `70000`, `131072`) coexist and
  `to_list` returns globally sorted order.
- Duplicate adds don't inflate `cardinality`.
- `union` merges correctly across containers.
- 5000 inserts in one container promote to bitmap; `has` still correct.

## Bug found while building the tutorial

`try_int(k, 0)` is not a runtime builtin (`to_int` exists but takes one
arg) — `union`/`to_list` crashed with `NameError`/`TypeError`. Inlined
copy uses `to_int(k)`. Flagged for a module fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/roaring_tutorial.ltl
python -m lateralus_lang check examples/roaring_tutorial.ltl
python -m pytest tests/test_roaring_tutorial.py -x -q
```
