# Near-Duplicate Detection with `stdlib/simhash.ltl`

SimHash fingerprints documents into 64 bits so near-duplicates compare
in O(1): tokenize, hash each token, and let each bit position vote.
Hamming distance between fingerprints approximates document similarity.

`stdlib/simhash.ltl` implements the full pipeline. Companion:
`examples/simhash_tutorial.ltl`.

---

## Pipeline

1. `simhash_tokenize` — splits on non-alphanumerics, ASCII-lowercases
2. `fingerprint` — per-token 64-bit hash, ±1 vote per bit, sign → bits
3. `hamming` — popcount of `a ^ b`
4. `similarity` — `1 - hamming/64`
5. `near_duplicate(a, b, threshold)` — hamming ≤ threshold
6. `fingerprint_all` — batch fingerprints

## Bugs found while building the tutorial

- `char_at()` is not a runtime builtin → `slice(i, i+1)`
- `xxhash_hash64()` is **called but defined nowhere in the repo** —
  the module cannot run as shipped. The tutorial substitutes an inline
  FNV-1a 64 hasher (same role; fingerprints remain deterministic).

## Verified behavior

- Fingerprints are deterministic across calls.
- Docs differing only by trailing punctuation: **hamming = 0**
  (identical token multiset).
- Unrelated doc: hamming = 35, similarity ≈ 0.45.
- `near_duplicate` respects the bit threshold; self-comparison = 0 bits.

## Running the tutorial

```bash
python -m lateralus_lang run examples/simhash_tutorial.ltl
python -m lateralus_lang check examples/simhash_tutorial.ltl
python -m pytest tests/test_simhash_tutorial.py -x -q
```
