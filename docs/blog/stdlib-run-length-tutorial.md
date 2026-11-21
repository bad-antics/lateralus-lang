# Run-Length Encoding with `stdlib/run_length.ltl`

Run-length encoding is the simplest compression there is: replace
each run of equal values with `(value, count)`. `stdlib/run_length.ltl`
implements it twice — once as nested `[value, count]` pairs that work
on **any** list element type, and once as a flat alternating
`value, count, value, count…` integer stream for compact int payloads —
plus a permille compression-ratio helper. ~75 lines, pure Lateralus,
zero dependencies.

Companion: `examples/rle_tutorial.ltl`.

---

## The two encodings

### `encode_pairs` / `decode_pairs` — generic

Walks the input once, tracking `cur` (current value) and `cnt`.
On a change it appends `[cur, cnt]` and resets. Works on ints,
strings, or any comparable element — the pairs are just two-element
lists.

```text
[7,7,7,3,3,9,9,9,9,1]  ->  [[7,3],[3,2],[9,4],[1,1]]
```

### `encode_packed` / `decode_packed` — flat ints

Flattens each pair into `value, count` integers:

```text
[[7,3],[3,2],[9,4],[1,1]]  ->  [7,3,3,2,9,4,1,1]
```

Half the list overhead — every element is a bare int, easy to feed
into fixed-width binary encoders. Decode steps `i += 2` and expands
each count.

## `ratio_permille`

```text
ratio_permille(orig_len, rle_pair_count)
  = (pair_count * 2 * 1000) / orig_len
```

Returns the encoded size as permille of the original — `1000` means
no compression, `800` means 20% smaller. Assumes the packed form
(2 ints per pair) and counts ints, not bytes. Guards `orig_len == 0`
by returning `1000`.

## Verified results

```text
[7,7,7,3,3,9,9,9,9,1] (10 elems)
  pairs  -> 4 pairs, first [7,3], last [1,1]
  packed -> [7,3,3,2,9,4,1,1]
  both decode round-trips equal the input
edge cases: [] -> 0 pairs; [5] -> [[5,1]];
  alternating [1,2,1,2] -> 4 pairs (worst case, expands)
ratios: (10,4)->800.0‰  (100,50)->1000.0‰  (0,0)->1000
```

`tests/test_rle_tutorial.py` pins every value above.

## When to use it

**Use it** for telemetry streams, bitmap-ish integer arrays,
simple-icon sprite rows, or anywhere values cluster into runs —
sparse counters, quantized sensor data, ASCII-art whitespace.

**Don't expect** real compression on high-entropy data: an
alternating list `[1,2,1,2,…]` produces *more* pairs than elements
(each run length 1). RLE wins only when runs exist; for general
payloads reach for `lz4` (see the sibling tutorial) instead.

That is `stdlib/run_length.ltl`: twenty lines of walking, two
encodings, one honest ratio — the codec you can hold in your head.
