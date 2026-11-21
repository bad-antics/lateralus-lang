# Fast Hashing with XXH64 in Lateralus

Every system that stores or routes data eventually needs a fingerprint that is
**fast, stable, and well distributed** — but not necessarily secret. Cache keys,
shard routing, deduplication, bloom-filter probes, file-integrity spot checks:
in all of these, a cryptographic hash like SHA-256 is overkill. You pay for
collision resistance against adversaries you do not have, and you pay for it on
every single call.

That is the niche of **xxHash**: a family of non-cryptographic hashes designed
by Yann Collet that trade adversarial guarantees for raw speed and excellent
bit dispersion. XXH64 — the 64-bit variant — is the workhorse inside
ClickHouse, RocksDB, Apache Parquet, and Zstd.

In this tutorial, we explore `stdlib/xxhash.ltl`, the Lateralus Spiral Wave 7
module that implements XXH64 **bit-for-bit identically to the canonical
Cyan4973/xxHash reference**, plus the FNV-1a 64-bit hash bundled alongside it.
Every number printed below is a real output of the module, cross-checked
against the official xxHash spec test vectors.

---

## The XXH64 Algorithm

XXH64 processes its input in three phases, using five 64-bit primes:

```text
PRIME64_1  0x9E3779B185EBCA87
PRIME64_2  0xC2B2AE3D27D4EB4F
PRIME64_3  0x165667B19E3779F9
PRIME64_4  0x85EBCA77C2B2AE63
PRIME64_5  0x27D4EB2F165667C5
```

All arithmetic is modulo 2⁶⁴ — in Lateralus, whose integers have arbitrary
precision, the module masks every intermediate result back to the low 64 bits
(the `u64` helper), which is exactly what makes the output bit-identical to
the C reference.

### Phase 1 — the stripe loop (inputs ≥ 32 bytes)

Long inputs are consumed in 32-byte *stripes*. Four accumulators are seeded
from the caller's seed, and each 8-byte little-endian lane of the stripe is
folded into one accumulator with a *round*: multiply by PRIME64_2, rotate
left by 31, multiply by PRIME64_1.

```lateralus
fn round64(acc: int, input: int) -> int {
    acc = u64(acc + u64(input * XXH_P2))
    acc = rotl64(acc, 31)
    return u64(acc * XXH_P1)
}
```

After all stripes, the accumulators are combined by rotating each by a
different amount (1, 7, 12, 18) and summing, then each accumulator is folded
back in with a *merge round* — a round against zero, XORed in, followed by
one more multiply-add:

```lateralus
fn merge_round(acc: int, val: int) -> int {
    val = round64(0, val)
    acc = acc ^ val
    return u64(u64(acc * XXH_P1) + XXH_P4)
}
```

Short inputs (< 32 bytes) skip this phase entirely and start from
`seed + PRIME64_5` instead.

### Phase 2 — the tail

Whatever remains — either the whole input, or the < 32 bytes left after the
last stripe — is folded in at the widest width available:

1. **8-byte chunks**: one `round64` against zero, XOR, rotate left 27,
   multiply by PRIME64_1, add PRIME64_4.
2. **One 4-byte chunk**: multiply by PRIME64_1, XOR, rotate left 23,
   multiply by PRIME64_2, add PRIME64_3.
3. **Single bytes**: multiply by PRIME64_5, XOR, rotate left 11,
   multiply by PRIME64_1.

The input *length* is added to the hash before the tail runs, so `"abc"` and
`"abd"` — and even `"abc"` and `"abc\0"` — live in different hash spaces.

### Phase 3 — the avalanche

Finally, the hash is passed through an avalanche finalizer. Each step XORs a
right-shifted copy of the value back into itself and multiplies by another
prime, so that flipping any single input bit flips about half of the output
bits:

```lateralus
h = h ^ (h >> 33)
h = u64(h * XXH_P2)
h = h ^ (h >> 29)
h = u64(h * XXH_P3)
h = h ^ (h >> 32)
```

---

## Exploring `stdlib/xxhash.ltl`

The module exposes four public functions:

```lateralus
pub fn hash64(buf: list, seed: int) -> int        // raw byte list
pub fn hash64_str(s: str, seed: int) -> int       // string convenience wrapper
pub fn fnv1a_64(buf: list) -> int                 // FNV-1a over a byte list
pub fn fnv1a_64_str(s: str) -> int                // FNV-1a over a string
```

### Seeds

The seed is not a key — XXH64 is not a MAC — it is a *hash-space selector*.
Two services that seed differently get uncorrelated fingerprints for the same
input, which is handy for independent sharding layers or for re-hashing a hot
key space. The tutorial verifies:

```text
xxh64('abc', seed=0) = 4952883123889572249
xxh64('abc', seed=1) = 13738734796240226568
```

### FNV-1a — the other hash in the module

Fowler–Noll–Vo (FNV-1a) is the simplest respectable hash in common use: start
from a fixed *offset basis*, then for each byte XOR it in and multiply by the
FNV prime:

```lateralus
pub fn fnv1a_64(buf: list) -> int {
    let h = 0xCBF29CE484222325
    let prime = 0x100000001B3
    let i = 0
    while i < len(buf) {
        h = (h ^ buf[i]) & XXH_MASK
        h = u64(h * prime)
        i = i + 1
    }
    return h
}
```

It is slower per byte and disperses worse than XXH64, but it is five lines
long, needs no tables, and is ideal for tiny keys in memory-tight code paths.
A useful sanity anchor: **the FNV-1a hash of the empty input is the offset
basis itself**, `0xCBF29CE484222325` = `14695981039346656037`. If your FNV
implementation prints anything else for `""`, it is wrong.

---

## Executable Tutorial: `examples/xxhash_tutorial.ltl`

The runnable tutorial is self-contained — the module implementation is
inlined, as in the other stdlib tutorials — and walks through five steps:

1. **Canonical spec vectors** — `""`, `"a"`, `"abc"` at seed 0.
2. **Every length class** — a 14-byte input (8-byte chunk + 4-byte chunk +
   2 trailing bytes) and a 72-byte input (two full stripes + 8-byte tail),
   plus a byte-list/string equivalence check.
3. **Seeds** — the same string in two hash spaces.
4. **FNV-1a** — offset basis, the spec value for `"a"`, and a longer key.
5. **Cache keys in practice** — determinism for a repeated key, avalanche
   for a one-character change.

### Running and Verifying

Run the example with `lateralus run`:

```bash
lateralus run examples/xxhash_tutorial.ltl
```

Output:

```text
=== LATERALUS STDLIB XXHASH TUTORIAL ===
STEP 1: Canonical XXH64 test vectors (seed 0)
  xxh64('')    = 17241709254077376921  (spec: 0xEF46DB3751D8E999)
  xxh64('a')   = 15154266338359012955  (spec: 0xD24EC4F1A98C6E5B)
  xxh64('abc') = 4952883123889572249  (spec: 0x44BC2CF5AD770999)
STEP 2: Every length class — tails and the 32-byte stripe loop
  xxh64('Hello, xxHash!') = 1836616885408546661  (14 bytes: 8 + 4 + 2 tail)
  xxh64(72-byte string)   = 9869445744007518376  (two full 32-byte stripes + 8-byte tail)
  hash64([97, 98, 99]) == hash64_str('abc'): True
STEP 3: Seeds — same input, different hash space
  xxh64('abc', seed=0) = 4952883123889572249
  xxh64('abc', seed=1) = 13738734796240226568
  seeds differ: True
STEP 4: FNV-1a 64-bit — the tiny-key variant in the same module
  fnv1a('')          = 14695981039346656037  (the FNV offset basis)
  fnv1a('a')         = 12638187200555641996  (spec: 0xAF63DC4C8601EC8C)
  fnv1a('lateralus') = 18229159603426106184
STEP 5: Cache keys in practice — stable, and avalanched
  key('GET /users/42') twice, identical: True
  key('GET /users/43') differs:          True
PINNED_VECTORS: xxh64_empty=17241709254077376921 xxh64_a=15154266338359012955 xxh64_abc=4952883123889572249 xxh64_abc_seed1=13738734796240226568 xxh64_hello=1836616885408546661 xxh64_long=9869445744007518376 fnv_empty=14695981039346656037 fnv_a=12638187200555641996 fnv_lateralus=18229159603426106184
```

### Analysis of Pinned Vectors

| Vector | Hex | Why it matters |
|---|---|---|
| `xxh64("")` | `0xEF46DB3751D8E999` | The most-quoted XXH64 value in existence; exercises the short path with *no* tail at all — pure seed + length + avalanche. |
| `xxh64("a")` | `0xD24EC4F1A98C6E5B` | A single trailing byte: the narrowest tail step. |
| `xxh64("abc")` | `0x44BC2CF5AD770999` | Three trailing bytes, and the byte-list form `hash64([97, 98, 99])` must agree with the string form. |
| `xxh64("Hello, xxHash!")` | `0x197CF9539342BF65` | 14 bytes = 8 + 4 + 2: the only tutorial vector that exercises **all three** tail widths in one input. |
| `xxh64(72 bytes)` | `0x88F7509D158F18A8` | Two full 32-byte stripes through all four accumulators and both merge rounds, plus an 8-byte tail. |
| `xxh64("abc", seed=1)` | `0xBEA9CA8199328908` | Proves the seed actually perturbs the short path (it enters before the length is added). |
| `fnv1a("")` | `0xCBF29CE484222325` | The offset basis — FNV's identity check. |
| `fnv1a("a")` | `0xAF63DC4C8601EC8C` | One XOR + one multiply away from the basis. |

These values are not just "whatever the program printed": the companion
test suite (`tests/test_xxhash_tutorial.py`) re-derives every one of them
with an independent reference implementation written directly from the
xxHash spec, and fails if the tutorial's pinned line ever drifts from the
spec — or from the module.

---

## When to Use Which

- **`hash64` / `hash64_str`** — your default fingerprint: cache keys, shard
  routing (`hash % num_shards`), dedup checks, change detection, test-vector
  and fixture IDs, bloom-filter probe derivation.
- **`fnv1a_64` / `fnv1a_64_str`** — tiny keys, embedded-style code, or when
  you want a hash you can re-derive on a napkin.
- **Neither** — for anything adversarial. XXH64 and FNV-1a are *not*
  collision-resistant against an attacker who chooses inputs; for integrity
  against tampering use the cryptographic modules (`stdlib/blake2s.ltl`,
  `stdlib/crypto.ltl`) instead.

---

## Composition in the Spiral Wave Performance Lane

XXH64 is the fingerprint primitive the other Wave 7 modules assume:

- **`lz4`**: frame checksums and block identity for the compression lane.
- **`roaring`**: hashing keys into bitmap shards.
- **`radix_sort`**: pre-partitioning large key sets by hash bucket before
  the sort.
- **`consistent_hash`** (Wave 6): swap its FNV-1a ring hash for XXH64 when
  you need better dispersion on short keys.

See `tests/stdlib_spiral_wave_7.ltl` for the module's own conformance
checks, including the same `0xEF46DB3751D8E999` empty-input vector pinned
here.
