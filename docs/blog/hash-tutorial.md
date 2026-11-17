# Hashing and Checksums with `stdlib.hash`

Every cache, shard router, and dedup pass starts with the same small
question: turn this string into a number, the same number every time.
`stdlib/hash.ltl` is Lateralus's answer — four classic string hashes,
three checksums, and the helpers that put them to work. This tutorial
walks through each function with test vectors you can verify against
the published references, then builds a tiny sharding demo on top.

All of the code below runs. The example lives at
`examples/hash_tutorial.ltl` and is exercised by
`tests/test_hash_tutorial.py`:

```bash
python scripts/run_hash_tutorial.py
# 21 pinned checks passed
# Sharding 3 keys across 8 buckets:
# alpha -> bucket 3
# beta -> bucket 7
# gamma -> bucket 2
```

## How the example runs

The Python backend does not yet resolve `import` of stdlib modules, so
the runner (`scripts/run_hash_tutorial.py`) feeds the compiler the
module source and the example source as one combined program — the
module itself is used exactly as published, never copied or edited.

One wrinkle: `stdlib/hash.ltl` calls two helpers the backend does not
yet provide, `xor` and `char_code`. The example defines both, in a
clearly marked compatibility section, so the module can run today:

```lateralus
fn xor(a: int, b: int) -> int {
    return a ^ b
}

fn char_code(c: str) -> int {
    return ord(c)
}
```

## The string hashes

### FNV-1a (32-bit)

Fowler/Noll/Vo, the default choice for hash tables: xor each byte into
the accumulator, then multiply by the FNV prime, keeping 32 bits.

```lateralus
fnv1a_32("")       // 2166136261  (the offset basis, 0x811C9DC5)
fnv1a_32("a")      // 3826002220  (0xE40C292C)
fnv1a_32("foobar") // 3214735720  (0xBF9CF968)
fnv1a_32("hello")  // 1335831723
```

These are the reference values published with the FNV specification,
so they double as a conformance check for the implementation.

### FNV-1a (64-bit)

Same algorithm, wider accumulator — with one caveat covered in
"Known deviations" below. Only the empty string is pinned:

```lateralus
fnv1a_64("")  // 14695981039346656037  (the 64-bit offset basis)
```

### DJB2

Dan Bernstein's hash: start at 5381, then `h = h * 33 + c` per byte.

```lateralus
djb2("")      // 5381
djb2("a")     // 177670
djb2("hello") // 261238937
```

### SDBM

The hash from the SDBM database engine: `h = c + h * 65599` per byte.

```lateralus
sdbm("")      // 0
sdbm("a")     // 97
sdbm("abc")   // 807794786
sdbm("hello") // 684824882
```

## The checksums

Checksums trade distribution quality for simplicity and standards
pedigree — reach for them when the other end of the wire expects one.

| Function     | Input       | Output    | Reference                        |
| ------------ | ----------- | --------- | -------------------------------- |
| `checksum8`  | `""`        | 0         | byte sum mod 256                 |
| `checksum8`  | `"abc"`     | 38        | 97 + 98 + 99 = 294, mod 256      |
| `fletcher16` | `"abcde"`   | 51440     | worked example, 0xC8F0           |
| `fletcher16` | `"abcdefgh"`| 1575      |                                  |
| `adler32`    | `""`        | 1         | RFC 1950                         |
| `adler32`    | `"Wikipedia"`| 300286872 | RFC 1950 worked example, 0x11E60398 |
| `adler32`    | `"hello"`   | 103547413 |                                  |

## Putting it to work: `bucket`

`bucket(key, num_buckets)` is `fnv1a_32(key) % num_buckets` — the
one-liner behind shard routing and cache partitioning:

```lateralus
bucket("hello", 16)  // 11
bucket("world", 16)  // 3
```

The example ends by sharding three cache keys across eight buckets:

```lateralus
let keys = ["alpha", "beta", "gamma"]
let i = 0
while i < len(keys) {
    let key = keys[i]
    print(key + " -> bucket " + str(bucket(key, 8)))
    i = i + 1
}
// alpha -> bucket 3
// beta -> bucket 7
// gamma -> bucket 2
```

## Known deviations (verified, not hidden)

Two parts of the module do not behave the way their docstrings
suggest on the current backend. Both are documented here with the
evidence from the pinned run; the tutorial deliberately pins no
vector that would bless the wrong behaviour.

1. **`fnv1a_64` never masks to 64 bits.** The accumulator grows
   without bound (Python integers do not wrap), so for non-empty
   input the result is the unmasked product, not the published
   FNV-1a-64 value. `fnv1a_64("a")` returns
   16158402040730025868984903134348; the published value is
   12638187200555641996 (0xAF63DC4C8601EC8C). Only the empty string
   agrees, which is why only it is pinned above.

2. **`combine` — and therefore `hash_list` — fails on the Python
   backend.** `combine` divides with `/`, which is float division in
   Lateralus, and passes the result to `xor`; the backend raises
   `TypeError: unsupported operand type(s) for ^: 'int' and 'float'`.
   Until the module uses integer division, treat `combine` and
   `hash_list` as unavailable on this backend and compose
   `fnv1a_32` yourself, as `bucket` does.

## Summary

- Use `fnv1a_32` (or `bucket`) for tables, caches, and sharding.
- Use `adler32` / `fletcher16` when a format or protocol asks for
  that exact checksum — the module matches the published vectors.
- Use `djb2` / `sdbm` when you need a second, independent hash
  (double hashing, bloom-style probes).
- Avoid `fnv1a_64` for interoperability until it masks, and avoid
  `combine` / `hash_list` on the Python backend for now.
