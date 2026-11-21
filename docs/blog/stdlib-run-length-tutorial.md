# Run-Length Encoding with `stdlib/run_length.ltl`

Run-length encoding is the oldest compression trick there is: replace
runs of identical values with `(value, count)` pairs. It is terrible
for photos and perfect for bitmaps, sparse telemetry, and RLE font
glyphs. `stdlib/run_length.ltl` ships two encodings plus a ratio
metric in about 73 lines.

This tutorial covers both wire shapes and the permille compression
ratio. Companion: `examples/run_length_tutorial.ltl`.

---

## Two encodings

**Pair encoding** — `encode_pairs` returns a list of `[value, count]`
tuples. Self-describing and safe for any element type:

```text
[1,1,1,2,2,3,3,3,3] → [[1,3],[2,2],[3,4]]
```

**Packed encoding** — `encode_packed` flattens the same pairs into a
single `value,count,value,count,…` integer stream. Half the list
overhead, but only valid when values are integers (the decoder steps
two slots at a time and silently ignores a dangling odd tail).

Both decoders round-trip exactly; the tutorial pins both.

## ratio_permille

`ratio_permille(orig_len, rle_pair_count)` expresses compression as
parts-per-thousand where **1000 = no compression** — a metric shape
borrowed from Prometheus-style ratios.

> Quirk worth knowing: the implementation divides with `/`, and
> Lateralus `/` yields **float** — so the function is annotated
> `-> int` but returns `600.0`, `888.8888888888889`, etc. The tutorial
> prints the real behaviour. A `floor()`-style fix is a candidate for
> a small follow-up PR.

## Edge cases

- empty input → `[]` (not `[[]]`)
- single element → `[[v,1]]`
- `orig_len == 0` → ratio `1000` (defined, avoids div-by-zero)

## Running the tutorial

```bash
python -m lateralus_lang run examples/run_length_tutorial.ltl
python -m lateralus_lang check examples/run_length_tutorial.ltl
python -m pytest tests/test_run_length_tutorial.py -x -q
```

The example inlines the module verbatim — `run_length.ltl` is pure
Lateralus with no external dependencies.
