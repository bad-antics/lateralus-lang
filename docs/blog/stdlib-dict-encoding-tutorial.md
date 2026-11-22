# Dictionary Encoding with `stdlib/dict_encoding.ltl`

Parquet's `PLAIN_DICTIONARY`, Arrow's `DictionaryArray`, every OLAP engine
worth its salt — they all do the same trick: when a column repeats a small
set of values (country codes, status flags, enum-like strings), store the
*distinct* values once and keep only integer references per row.

`stdlib/dict_encoding.ltl` is that trick in 63 lines: `encode` produces a
`{dictionary, indices}` pair, `decode` reverses it, and two tiny helpers
tell you the cardinality and the bit-width your indices need.

This tutorial walks the encoding, the decode round-trip, and the
cardinality edge cases, with a runnable companion
(`examples/dict_encoding_tutorial.ltl`) pinned by pytest.

---

## The encoding

```text
values:   ["red","green","red","blue","green","red","yellow","blue"]
dictionary: ["red","green","blue","yellow"]     <- first-seen order
indices:    [0,    1,      0,    2,     1,      0,    3,        2   ]
```

`encode` walks the input once, maintaining a `str(value) → index` map.
First sight of a value appends it to `dictionary` and records the new
index; repeats reuse it. Two details worth noting:

- **Keys are `str(v)`** — `10` and `"10"` collide intentionally, matching
  how columnar formats treat dictionary keys as strings.
- **Dictionary order is first-seen**, not sorted — deterministic for a
  given input, which is what makes the encoding reproducible.

## Decode and the round-trip

`decode` is a straight gather: `out[i] = dictionary[indices[i]]`. Because
every index was minted by `encode`, the round-trip is exact —
`decode(encode(xs)) == xs` for any list, verified in the companion's
STEP 5.

## Cardinality and bit width

```text
cardinality(enc)   = len(dictionary)
index_bit_width(enc) = bits needed for max index = ceil(log2(card))
```

For our 8-row / 4-distinct example: cardinality 4, bit width 2 — indices
0–3 fit in two bits. The helper counts bits by shifting `n-1` right until
zero, which is exactly `ceil(log2(n))` for `n > 1` and returns 1 for
`n <= 1` (you still need a bit to store a single index 0).

This is the number a real columnar writer cares about: `bit_width ×
row_count` is the payload size of the indices array, versus
`avg_value_size × row_count` uncompressed. On a 1M-row column with 16
distinct values you go from ~8MB of strings to 2MB of 4-bit indices plus
a 16-entry dictionary.

## Edge cases

| Input | dictionary | indices | card | width |
|---|---|---|---|---|
| `[]` | `[]` | `[]` | 0 | n/a |
| `["only"]` | `["only"]` | `[0]` | 1 | 1 |
| mixed `[10,20,10]` | `[10,20]` | `[0,1,0]` | 2 | 1 |

Empty input encodes cleanly (empty lists, no crash); a single distinct
value pins width at 1 rather than 0 — a 0-bit index would be a divide-by-
zero waiting to happen downstream.

## Running the companion

```text
=== LATERALUS STDLIB DICT_ENCODING TUTORIAL ===
STEP 1 dict: red,green,blue,yellow
STEP 2 indices: 0,1,0,2,1,0,3,2
STEP 3 cardinality = 4
STEP 4 bit_width = 2
STEP 5 round-trip equal: True
STEP 6 int dict: 10,20,30
STEP 7 int indices: 0,1,0,2,1,0
STEP 8 single card=1 width=1
STEP 9 empty card=0 indices=[]
PINNED_VECTORS: dict=red,green,blue,yellow idx=0,1,0,2,1,0,3,2 card=4 width=2 rt=true nums=10,20,30 nidx=0,1,0,2,1,0 single=1/1
```

`tests/test_dict_encoding_tutorial.py` pins the transcript — including
STEP 4's `bit_width = 2` (the easy value to get wrong: `ceil(log2(4))`
is 2, not 3) and STEP 5's round-trip equality.

## When to use it

**Use it** when profiling shows a column with low cardinality —
categorical strings, enums, repeated IDs, timestamps truncated to a
day. The module is intentionally minimal: no run-length encoding, no
frame-of-reference, no bit-packing of the indices themselves. It gives
you the dictionary+indices pair; packing those indices at `bit_width`
bits is the next layer down (and a good exercise for a follow-up port).

**Don't bother** for high-cardinality columns (unique IDs, floats,
hashes) — the dictionary would be as large as the data and you'd pay
for the indirection twice.

That is `stdlib/dict_encoding.ltl`: 63 lines, four public functions, and
a companion script that proves `decode(encode(xs)) == xs` on the pinned
vectors.
