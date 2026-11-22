# Caching with `stdlib/lru.ltl`

The LRU (Least Recently Used) cache evicts the oldest-touched entry when
full — the standard bounded cache behind memoization, HTTP caches, and
connection pools. `stdlib/lru.ltl` implements one as a map of
data + recency-ordered key list.

This tutorial exercises every operation. Companion:
`examples/lru_tutorial.ltl`.

---

## Model

`{data: {key→value}, order: [keys LRU→MRU], capacity, hits, misses}`.
`get`/`put` move touched keys to the end of `order`; eviction removes
`order[0]`.

## API

- `new(capacity)`, `from_pairs(pairs, capacity)`
- `get` → `[cache, value]` (value `nil` on miss; **hits/misses counters**
  update — note `get` on a missing key does *not* insert)
- `put`, `remove`, `has` (peek — does not update recency)
- `size`, `capacity`, `is_empty`, `is_full`, `hits`, `misses`,
  `hit_rate`, `all_keys` (LRU→MRU order), `stats`
- `clear` (also resets hit/miss counters), `resize` (evicts oldest
  when shrinking)

## Verified behaviors

- Recency: `get("a")` moves `a` to MRU — next eviction takes the true
  LRU, not insertion order.
- `from_pairs` with more pairs than capacity keeps the most recent.
- `remove` of a missing key is a no-op; `has` doesn't disturb order.

No source changes were needed — the module ran cleanly as inlined.

## Running the tutorial

```bash
python -m lateralus_lang run examples/lru_tutorial.ltl
python -m lateralus_lang check examples/lru_tutorial.ltl
python -m pytest tests/test_lru_tutorial.py -x -q
```
