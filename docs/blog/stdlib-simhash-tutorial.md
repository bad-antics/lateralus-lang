---
title: "Near-Duplicate Detection with stdlib.simhash"
date: 2026-04-20
author: bad-antics
tags: [stdlib, simhash, hashing, tutorial]
---

# Near-Duplicate Detection with `stdlib.simhash`

SimHash is a *locality-sensitive* hash: unlike a cryptographic hash, where a
one-bit input change flips about half the output bits, SimHash maps **similar
inputs to similar fingerprints**. Two documents that share most of their tokens
produce 64-bit fingerprints that differ in only a few bits. That makes it ideal
for near-duplicate detection, plagiarism screening, and log de-noising.

This tutorial walks through the algorithm, the Lateralus API, and the pinned
test vectors that guard the implementation.

## 1. How SimHash works

1. **Tokenize** the input (words, shingles, or n-grams).
2. **Hash** each token to a 64-bit value with XXH64 (seed 0).
3. Keep a 64-slot signed accumulator `v[0..63]`. For every token hash `h` and
   every bit position `i`: add `+1` to `v[i]` if bit `i` of `h` is set,
   otherwise add `-1`.
4. The fingerprint has bit `i` set iff `v[i] > 0`.
5. **Compare** two fingerprints with Hamming distance (popcount of the XOR).
   A small distance means the inputs are similar.

## 2. Pinned XXH64 test vectors

Because SimHash is built entirely on XXH64, a bug in the hash primitive
silently corrupts every fingerprint. We therefore pin known-good vectors.
These were verified by independently reimplementing XXH64 and matching both the
canonical reference outputs and the repository's own pinned constant.

| Input (UTF-8) | Seed | XXH64 (hex)            |
|---------------|------|------------------------|
| `""` (empty)  | 0    | `0xEF46DB3751D8E999`   |
| `"abc"`       | 0    | `0x44BC2CF5AD770999`   |

The empty-input value `0xEF46DB3751D8E999` is the well-known XXH64 of the empty
string with seed 0 and matches the constant already pinned in the repository.

## 3. Runnable example

```lateralus
-- examples/simhash_near_duplicates.ltl
use stdlib.simhash

fn tokens(text) {
    text |> lowercase |> split_words
}

let a = "the quick brown fox jumps over the lazy dog"
let b = "the quick brown fox leaps over the lazy dog"
let c = "completely unrelated sentence about compilers"

let fa = a |> tokens |> simhash.fingerprint
let fb = b |> tokens |> simhash.fingerprint
let fc = c |> tokens |> simhash.fingerprint

print("distance(a, b) = {simhash.hamming(fa, fb)}")   -- small (similar)
print("distance(a, c) = {simhash.hamming(fa, fc)}")   -- large (different)

-- Treat fingerprints within 3 bits as near-duplicates
let is_dup = simhash.hamming(fa, fb) <= 3
print("a ~ b near-duplicate? {is_dup}")
```

Expected behaviour: `distance(a, b)` is much smaller than `distance(a, c)`.
Unrelated text lands near 32 bits apart on average (random 64-bit strings),
while near-identical text lands within a handful of bits.

## 4. Choosing a threshold

| Hamming distance | Interpretation                       |
|------------------|--------------------------------------|
| 0                | Identical token multiset             |
| 1 - 3            | Near-duplicate (typical threshold)   |
| 4 - 10           | Related / heavily edited             |
| ~32              | Unrelated (random expectation)       |

For large corpora, index fingerprints by 16-bit bands to find candidates with
distance <= 3 in sub-linear time (pigeonhole: if two 64-bit values differ in at
most 3 bits, at least one of four 16-bit bands matches exactly).

## 5. Guarding against regressions

The test file `tests/test_simhash_vectors.py` asserts the XXH64 vectors above
and basic SimHash properties:

```python
# tests/test_simhash_vectors.py
import pytest

XXH64_VECTORS = [
    (b"",    0, 0xEF46DB3751D8E999),
    (b"abc", 0, 0x44BC2CF5AD770999),
]

@pytest.mark.parametrize("data,seed,expected", XXH64_VECTORS)
def test_xxh64_pinned(data, seed, expected):
    from lateralus_lang.stdlib import simhash
    assert simhash.xxh64(data, seed) == expected

def test_identical_inputs_distance_zero():
    from lateralus_lang.stdlib import simhash
    fp = simhash.fingerprint(["a", "b", "c"])
    assert simhash.hamming(fp, fp) == 0

def test_similar_closer_than_unrelated():
    from lateralus_lang.stdlib import simhash
    base = "the quick brown fox jumps over the lazy dog".split()
    near = "the quick brown fox leaps over the lazy dog".split()
    far = "completely unrelated sentence about compilers".split()
    fb = simhash.fingerprint(base)
    assert simhash.hamming(fb, simhash.fingerprint(near)) < \
           simhash.hamming(fb, simhash.fingerprint(far))
```

If the XXH64 primitive ever drifts (endianness bug, wrong prime constant,
off-by-one in the tail loop), the pinned vectors fail immediately, long before
a subtle fingerprint mismatch could reach production.

## Summary

- SimHash = weighted bit-vote over per-token XXH64 hashes.
- Compare with Hamming distance; <= 3 bits is a good near-duplicate cutoff.
- Pin your hash vectors so the whole pipeline stays trustworthy.