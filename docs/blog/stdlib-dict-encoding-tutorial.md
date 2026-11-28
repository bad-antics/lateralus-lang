# Dictionary Encoding with `stdlib/dict_encoding.ltl`

Dictionary encoding replaces repeated values in a column with a small dictionary and integer indices. The dictionary keeps the first-seen order, so decoding reproduces the input exactly while low-cardinality columns use compact indices.

The companion example is `examples/dict_encoding_tutorial.ltl`. It inlines the standard-library functions so it can run without imports or network access.

## The encoded shape

`encode(values)` returns a map with two fields.

- `dictionary` contains each distinct value once, in first-seen order.
- `indices` contains one integer per input value.

For `['pending', 'paid', 'pending', 'failed']`, the result is equivalent to:

```text
dictionary = ['pending', 'paid', 'failed']
indices = [0, 1, 0, 2]
```

`decode(encoded)` walks the indices and looks up the corresponding dictionary value. The round-trip is exact for empty columns, single-value columns, and mixed values whose `str` representations are distinct.

## Cardinality and index width

`cardinality(encoded)` returns the dictionary length. `index_bit_width(encoded)` returns `ceil(log2(cardinality))`, with a minimum of one bit. This describes the width of an index stream after the dictionary is stored once. It does not estimate the memory used by the dictionary itself.

The width is based on `n - 1`, so powers of two remain exact. A dictionary of three values needs two bits, while a dictionary of four values also needs two bits.

## Repeated status values

Dictionary encoding is useful for status columns because the same small vocabulary appears many times. The example filters pending rows by their encoded code, decodes the column, and verifies that the original order is preserved.

The implementation uses `str(value)` as its lookup key. Keep that behavior in mind when encoding mixed types whose string forms could collide. If a column needs type-sensitive equality, normalize it before encoding.

## Running the tutorial

```bash
python -m lateralus_lang run examples/dict_encoding_tutorial.ltl
python -m lateralus_lang check examples/dict_encoding_tutorial.ltl
python -m pytest tests/test_dict_encoding_tutorial.py -x -q
```

The pinned vectors in the output cover first-seen ordering, round-trip decoding, empty and single-value inputs, status filtering, and the index-width boundary.
