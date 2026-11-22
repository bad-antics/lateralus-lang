# proto3 on the Wire with `stdlib/protobuf.ltl`

Protobuf's wire format is delightfully small: a varint key packing
`field_number << 3 | wire_type`, then a value whose encoding depends
on the wire type — varint, fixed32, fixed64, or length-delimited
bytes. No schema needed at the byte level. `stdlib/protobuf.ltl`
implements that layer in ~180 lines: primitives in, byte-exact wire
data out, and a decoder that walks fields back.

This tutorial covers every wire type with verified hex. Companion:
`examples/protobuf_tutorial.ltl`.

---

## Varints and zig-zag

`enc_varint` emits base-128 little-endian groups with the continuation
bit — `300` becomes `ac 02`. `dec_varint` returns `[value, next_index]`
so callers can chain.

Signed integers can't use plain varints (negative int32 would take 10
bytes), so proto3 uses **zig-zag**: `-1 → 1`, `-2 → 3`, `n → 2n`. The
module's `zz_encode`/`zz_decode` are exact inverses — verified for
both directions.

## The tag byte

```text
enc_tag(field_number, wire_type) = varint(field_number << 3 | wire_type)
```

Field 5 + varint → `0x28`; field 16 + length-delimited → `0x82 0x01`
(two-byte varint — field numbers above 15 exercise multi-byte tags).
`dec_tag` splits it back into `[field_number, wire_type, next_i]`.

## Wire types

| Wire type | Name | Used for |
|---|---|---|
| 0 | varint | int32/64, bool, enum, sint (zig-zag) |
| 1 | fixed64 | double, fixed64, sfixed64 |
| 2 | length-delimited | string, bytes, embedded messages |
| 5 | fixed32 | float, fixed32, sfixed32 |

- `enc_int32` / `enc_sint32` / `enc_bool` — tag + varint
- `enc_string` / `enc_bytes` / `enc_message` — tag + varint length +
  payload (`enc_message` takes an already-serialized sub-message, so
  nesting is just composition)
- `enc_fixed32` / `enc_fixed64` — **little-endian** byte order
  (`0x01020304` → `04 03 02 01`)

## Decoding

`dec_field(buf, i)` returns `[field_number, wire_type, value,
next_i]` — `value` is an int for varint/fixed types, a byte list for
length-delimited. `decode_message` loops it into a map keyed by field
number. For repeated fields or typed decoding you drive `dec_field`
yourself in a loop — the module deliberately stays schema-free.

A full round-trip in the companion: a 25-byte message containing a
string, an int, a bool, a nested message, and a fixed32 decodes back
to every field, and the nested message decodes recursively.

## Verified output

```text
varint(300)            = ac02
zz(-1)                 = 01        (zig-zag)
field5-varint tag      = 28
field16-bytes tag      = 8201      (multi-byte varint tag)
int32 f1=150           = 089601
string f4="hi"         = 22026869
fixed64 f6=0102030405060708 = 310807060504030201  (LE)
```

`tests/test_protobuf_tutorial.py` pins every byte string.

## When to use it

**Use it** for embedded RPC payloads, log records, or any protocol
where you control both ends and want protobuf's compactness without a
schema compiler. Great for round-tripping known-shape messages.

**Don't expect** `.proto` parsing, generated types, packed repeated
fields, maps, or unknown-field retention semantics — `decode_message`
keys by field number and keeps the last value per field. For real
protobuf workloads use a codegen'd library.

That is `stdlib/protobuf.ltl`: varints in, fields out — the wire
format, nothing more, nothing less.
