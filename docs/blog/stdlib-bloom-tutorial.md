# Fast Probabilistic Deduplication with Lateralus `stdlib/bloom.ltl`

When building high-throughput network applications, distributed databases, or search scrapers, testing whether a key has been observed is one of the most frequent hot paths. Storing millions of full strings or hashes in an in-memory hash set quickly exhausts RAM.

A **Bloom filter** provides a constant-time, space-efficient probabilistic data structure that answers membership queries with **zero false negatives**:
- If `contains_key` returns `false`, the item is **guaranteed** never to have been inserted.
- If `contains_key` returns `true`, the item is *probably* present, with a false-positive probability bounded by the filter's sizing parameters.

Lateralus includes a production-grade, zero-external-dependency Bloom filter implementation in `stdlib/bloom.ltl`.

---

## 1. Mathematical Architecture & The Double-Hashing Trick

A classical Bloom filter with $m$ bits and $k$ independent hash functions can be expensive to compute if each hash requires an independent cryptographic round.

`stdlib/bloom.ltl` utilizes the **Kirsch–Mitzenmacher technique** (`hash_positions`), which generates $k$ simulated independent hash functions using only two evaluations of FNV-1a (32-bit and 64-bit):

$$h_i(x) = (h_1(x) + i \cdot h_2(x)) \pmod m$$

By enforcing that $h_2(x)$ is odd (`h2 = h2 | 1`), the stride between successive probes is coprime with power-of-two word boundaries, guaranteeing uniform bit dispersion.

### Optimal Sizing Formulas
Given an expected element capacity $n$ and an acceptable false-positive probability $p$:

$$m = -\frac{n \ln p}{(\ln 2)^2} \approx -1.44 \cdot n \cdot \log_2(p)$$

$$k = \frac{m}{n} \ln 2 \approx 0.693 \cdot \frac{m}{n}$$

`stdlib/bloom.ltl` exposes `optimal_params(n, fp_per_1000)` which calculates these parameters with fast integer arithmetic, eliminating the need to import floating-point math libraries in resource-constrained runtimes.

---

## 2. Core API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `bloom_new_filter` | `(m: int, k: int) -> map` | Allocates a 32-bit packed bitset with $m$ bits and $k$ hashes. |
| `bloom_optimal_params` | `(n: int, fp_per_1000: int) -> list` | Calculates $[m, k]$ for expected count $n$ and false positive rate. |
| `bloom_add` | `(f: map, key: str)` | Hashes the key and sets the $k$ corresponding bits. |
| `bloom_contains_key` | `(f: map, key: str) -> bool` | Checks if all $k$ bit positions are set. Early exits on first 0. |
| `bloom_fill_ppt` | `(f: map) -> int` | Returns the bit density in parts-per-thousand ($[0, 1000]$). |
| `bloom_union` | `(a: map, b: map) -> map` | Bitwise OR of two identically-sized filters ($A \cup B$). |
| `bloom_intersect` | `(a: map, b: map) -> map` | Bitwise AND of two identically-sized filters ($A \cap B$). |

---

## 3. Practical Example: Guarding Backend Queries

Here is how to create a filter, size it dynamically, check URL membership, and inspect the bit saturation:

```lateralus
import bloom

pub fn main() {
    // 1. Target 10,000 items with a 1% false positive rate (10 per 1000)
    let params = bloom_optimal_params(10000, 10)
    let m = params[0]
    let k = params[1]

    let filter = bloom_new_filter(m, k)

    // 2. Add elements
    bloom_add(filter, "https://lateralus.org/docs")
    bloom_add(filter, "https://lateralus.org/blog")

    // 3. Fast rejection test
    if not bloom_contains_key(filter, "https://lateralus.org/secret") {
        // Guaranteed not present: skip disk I/O completely!
        print("Bypass disk cache lookup")
    }

    // 4. Fill ratio check
    let ppt = bloom_fill_ppt(filter)
    print("Filter saturation: " + str(ppt) + "/1000")
}
```

---

## 4. Set Operations: Merging Sharded Partitions

Because Bloom filters are represented as packed bit arrays (`bits[w] = bits[w] | (1 << b)`), merging two filters that share the same $(m, k)$ configuration is an $O(m/32)$ bitwise operation:

```lateralus
let cluster_union = bloom_union(shard_a, shard_b)
let cluster_intersect = bloom_intersect(shard_a, shard_b)
```

This allows distributed worker nodes to collect local Bloom filters during map-reduce passes and send them over the wire to be merged with zero item-by-item deserialization overhead.

---

## 5. Verification & Testing

The canonical test suite in `tests/stdlib_bloom_tutorial.ltl` verifies:
1. **Zero False Negatives**: 100% retrieval of inserted items.
2. **Optimal Parameter Sizing**: Bounds check for bit allocations across key ranges.
3. **Set Algebra**: Distributive properties of union and intersection.
4. **Saturation Monitoring**: Monotonically non-decreasing popcount and fill ratio.

Run the test suite locally:
```bash
python -m lateralus_lang check tests/stdlib_bloom_tutorial.ltl
python -m lateralus_lang check examples/bloom_tutorial.ltl
```
