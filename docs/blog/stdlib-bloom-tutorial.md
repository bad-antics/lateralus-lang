# Probabilistic Membership with `stdlib/bloom.ltl`

A Bloom filter answers "is this key *probably* present?" in O(k) — no
stored keys, tiny memory, false positives possible but never false
negatives. This module adds double hashing (Kirsch–Mitzenmacher) so
k positions come from just two FNV-1a hashes.

This tutorial exercises optimal_params, new_filter/add/contains_key,
fill stats, and union/intersect. Companion:
`examples/bloom_tutorial.ltl`.

---

## How it works

- Bit array packed into 32-bit words; `add` sets k hashed positions
- `contains_key` returns true only if *all* k bits are set →
  false positives possible, false negatives impossible
- `optimal_params(n, fp_per_1000)` picks m and k for a target FP rate
- `union`/`intersect` merge filters of identical shape (m, k)

## Verified vectors

`optimal_params(100, 10)` → `[900, 9]` (~1% FP); `(100, 1)` →
`[1200, 12]` (~0.1%). On a 128-bit filter with 3 keys: apple→true,
durian→false, 2/500 probes false-positive, fill 93.75 ppt.

## Bugs found while building the tutorial (module cannot run as shipped)

1. `import hash` transpiles to `import hash` — no such Python module;
   inlined fnv1a_32/64 instead.
2. Calls `hash_fnv1a_32/64` but `stdlib/hash.ltl` exports
   `fnv1a_32/64` — name mismatch → `NameError`.
3. `char_code` and `xor` are not runtime builtins → `ord(slice(...))`
   and `^`.
4. `/` yields float → `int()` around `/32` word-index math.
5. `probe` is a reserved keyword — renamed in tutorial only.

All fixes are inlined in the tutorial copy and flagged for a module
fix PR; the shipped `stdlib/bloom.ltl` is unchanged.

## Running the tutorial

```bash
python -m lateralus_lang run examples/bloom_tutorial.ltl
python -m lateralus_lang check examples/bloom_tutorial.ltl
python -m pytest tests/test_bloom_tutorial.py -x -q
```
