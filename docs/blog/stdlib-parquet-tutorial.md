# Parquet File Framing with `stdlib/parquet.ltl`

Parquet is the columnar storage format under Delta Lake, Iceberg, and
most of the modern lakehouse. Its on-disk envelope is deliberately
small: a `PAR1` magic, row-group column chunks, a Thrift-serialised
`FileMetaData` footer, a little-endian footer length, and a closing
`PAR1`. `stdlib/parquet.ltl` implements exactly that envelope — magic
constants, footer framing and parsing, Thrift compact-protocol integer
primitives, and the stable data-page-v1 header fields — in about 135
lines.

This tutorial covers the file layout, footer-pointer parsing, the
zigzag/uvarint encoding Thrift uses for integers, and the page-header
shape. Companion: `examples/parquet_tutorial.ltl`.

> Scope note: the module does **not** ship a full Thrift encoder. It
> provides the compact-protocol primitives so callers can hand-roll
> `FileMetaData` — the tutorial does the same.

---

## File envelope

```text
"PAR1" magic
<row groups: column chunks of pages>
<FileMetaData (Thrift)>
<i32 LE: footer length>
"PAR1" magic
```

`assemble_file(body, footer)` wraps finished parts into the full
byte list; `parse_footer_pointer(buf)` reads the last 8 bytes —
verifies the trailing magic, extracts the footer length, and computes
the footer offset. Both reject malformed input (`nil` on short buffers
or bad magic).

## Footer length encoding

The footer length is a signed i32 in **little-endian** — `enc_i32_le`
emits four bytes LSB-first and folds negatives into the unsigned range
first (`v + 0x100000000`), matching two's-complement on disk.

## Thrift compact protocol integers

Thrift's compact protocol encodes integers in two steps:

1. **Zigzag** maps signed → unsigned: `zz(n) = (n << 1) ^ (n >> 31)`
   for i32 (and the 63-bit variant for i64). Small magnitudes stay
   small: `1 → 2`, `-1 → 1`, `64 → 128`.
2. **Uvarint** splits the result into 7-bit groups, little-endian,
   with the high bit set on every group except the last:
   `300 → [172, 2]` (`0xAC` = `0b0101100 | 0x80`, then `0x02`).

`thrift_varint_i32`/`_i64` compose the two. `thrift_binary` prefixes a
byte string with its uvarint length; `thrift_string` is the same over a
Lateralus string.

## Data page v1 header

`data_page_v1_header` returns the logical header fields —
`num_values`, `encoding`, `definition_level_encoding`,
`repetition_level_encoding` — as a map. Real encoders wrap these in
Thrift field IDs themselves because implementations cache them.

## Running the tutorial

```bash
python -m lateralus_lang run examples/parquet_tutorial.ltl
python -m lateralus_lang check examples/parquet_tutorial.ltl
python -m pytest tests/test_parquet_tutorial.py -x -q
```

The example is self-contained: module code inlined with a local
`bytes_of` ASCII shim (the module only uses it for `thrift_string`).
