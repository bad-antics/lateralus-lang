# Column Compression with `stdlib/frame_of_reference.ltl`

Frame-of-Reference is how Parquet, Lucene DocValues, and BtrBlocks
shrink integer columns: subtract the min once, store small deltas that
bit-pack tightly. The module also ships a Gorilla-style
delta-of-delta codec for monotonic timestamps.

This tutorial exercises both codecs — including a real edge-case bug.
Companion: `examples/frame_of_reference_tutorial.ltl`.

---

## API

- `encode(xs)` → `{ref, deltas, bit_width}`; `decode` reverses it
- `encode_dod(xs)` → `{first, second_delta, dods}`; `decode_dod`
  reverses it — second differences collapse steady timestamp streams
  to mostly zeros

## Verified behavior

- `[100,101,105,110,115]` → ref 100, deltas `[0,1,5,10,15]`,
  bit_width 4 — perfect round-trip.
- Negative ranges, empty, single-element, and constant columns all
  round-trip.
- Timestamp series `[1000,1010,1025,1040,1070,1100]` → dods
  `[5,0,15,0]` — round-trips exactly.

## Real bug documented (not silently fixed)

`encode_dod([5, 5])` produces `{first:5, second_delta:0, dods:[]}` —
identical to the 1-element encoding — so `decode_dod` returns `[5]`,
**losing an element**. Any 2-element input with equal values hits this.
The tutorial prints the failure rather than hiding it; a proper fix
needs an explicit element count in the encoding. Flagged for a module
fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/frame_of_reference_tutorial.ltl
python -m lateralus_lang check examples/frame_of_reference_tutorial.ltl
python -m pytest tests/test_frame_of_reference_tutorial.py -x -q
```
