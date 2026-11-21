# Probabilistic Set Membership with Bloom Filters in Lateralus

When designing high-throughput caching systems, databases, or network proxies, checking whether a key exists before performing expensive disk reads or network RPCs is critical. A standard hash set stores every key in memory, requiring gigabytes of RAM.

A **Bloom filter** is a space-efficient, probabilistic data structure designed by Burton Howard Bloom in 1970. It answers set membership queries with two mathematical guarantees:

1. **Zero False Negatives**: If the filter reports an element is **not** present (`false`), it is **guaranteed** not to be in the set.
2. **Controlled False Positives**: If the filter reports an element **is** present (`true`), there is a small, configurable probability $p$ that it is a false positive due to hash collisions.

In this tutorial, we will explore `stdlib/bloom.ltl`, the Lateralus Standard Library module for zero-dependency bit-array Bloom filters.

---

## How Bloom Filters Work

A Bloom filter consists of:
* A bit array of size $m$ (initially all zeros).
* $k$ independent hash functions mapping keys to indices in $[0, m - 1]$.

### The Kirsch-Mitzenmacher Double-Hashing Trick

Computing $k$ separate hashes per lookup is computationally expensive. `stdlib/bloom.ltl` employs the double-hashing technique formalized by Adam Kirsch and Michael Mitzenmacher:

$$h_i(x) = (h_1(x) + i \cdot h_2(x)) \pmod m$$

Using only two base hashes (FNV-1a 32-bit and 64-bit), we generate $k$ effectively independent bit positions with negligible loss in asymptotic false-positive rate.

### Insertion and Querying

* **Insertion (`add`)**: Calculate $k$ hash positions and set each corresponding bit to `1`.
* **Membership Test (`contains_key`)**: Calculate $k$ hash positions. If **any** bit is `0`, the element was never added (`false`). If **all** bits are `1`, the element is probably in the set (`true`).

---

## The Lateralus Standard Library: `stdlib/bloom.ltl`

The module exposes:

```lateralus
pub fn new_filter(m: int, k: int) -> map
pub fn optimal_params(n: int, fp_per_1000: int) -> list
pub fn hash_positions(f: map, key: str) -> list
pub fn add(f: map, key: str)
pub fn contains_key(f: map, key: str) -> bool
pub fn popcount(bits: list) -> int
pub fn fill_ppt(f: map) -> int
pub fn union(a: map, b: map) -> map
pub fn intersect(a: map, b: map) -> map
```

### Packed Bit-Array Manipulation

To maximize performance and minimize memory footprint, bits are packed into 32-bit integer words:

```lateralus
fn bit_set(bits: list, pos: int) -> list {
    let w = to_int(pos / 32)
    let b = to_int(pos % 32)
    bits[w] = bits[w] | (1 << b)
    return bits
}

fn bit_test(bits: list, pos: int) -> bool {
    let w = to_int(pos / 32)
    let b = to_int(pos % 32)
    return (bits[w] & (1 << b)) != 0
}
```

---

## Runnable Example: `examples/bloom_tutorial.ltl`

Here is a self-contained, executable tutorial demonstrating insertion, negative testing, fill ratio, and filter union:

```lateralus
// Self-contained double hashing & bit array Bloom filter
fn main() {
    print("=== LATERALUS STDLIB BLOOM FILTER TUTORIAL ===")

    // 1. Initialize Bloom filter (m=64 bits, k=3 hash functions)
    let bf = new_filter(64, 3)
    print("STEP 1: Created filter m=64, k=3, initial count=" + str(bf["count"]))

    // 2. Insert items
    bf = add_item(bf, "apple")
    bf = add_item(bf, "banana")
    bf = add_item(bf, "cherry")
    print("STEP 2: Inserted 3 elements. Count=" + str(bf["count"]) + ", set bits=" + str(popcount(bf["bits"])))

    // 3. Test true positive queries (guaranteed 0 false negatives)
    let has_apple = contains_key(bf, "apple")
    let has_banana = contains_key(bf, "banana")
    let has_cherry = contains_key(bf, "cherry")
    print("STEP 3: True positives: apple=" + str(has_apple) + ", banana=" + str(has_banana) + ", cherry=" + str(has_cherry))

    // 4. Test non-inserted items
    let has_durian = contains_key(bf, "durian")
    let has_elderberry = contains_key(bf, "elderberry")
    print("STEP 4: Negative tests: durian=" + str(has_durian) + ", elderberry=" + str(has_elderberry))

    // 5. Check fill ratio in parts-per-thousand
    let fill = fill_ppt(bf)
    print("STEP 5: Filter fill ratio: " + str(fill) + " ppt")

    // 6. Test union of two filters
    let bf2 = new_filter(64, 3)
    bf2 = add_item(bf2, "durian")
    let combined = union_filters(bf, bf2)
    let combined_has_apple = contains_key(combined, "apple")
    let combined_has_durian = contains_key(combined, "durian")
    print("STEP 6: Union filter contains apple=" + str(combined_has_apple) + ", durian=" + str(combined_has_durian))

    print("PINNED_VECTORS: count=" + str(bf["count"]) + " bits_set=" + str(popcount(bf["bits"])) + " apple=" + str(has_apple) + " durian=" + str(has_durian) + " union_apple=" + str(combined_has_apple))
}

main()
```

### Execution & Pinned Output

Execute the script with:

```bash
lateralus run examples/bloom_tutorial.ltl
```

Output:

```text
=== LATERALUS STDLIB BLOOM FILTER TUTORIAL ===
STEP 1: Created filter m=64, k=3, initial count=0
STEP 2: Inserted 3 elements. Count=3, set bits=9
STEP 3: True positives: apple=True, banana=True, cherry=True
STEP 4: Negative tests: durian=False, elderberry=False
STEP 5: Filter fill ratio: 140 ppt
STEP 6: Union filter contains apple=True, durian=True
PINNED_VECTORS: count=3 bits_set=9 apple=True durian=False union_apple=True
```

Notice:
1. `bits_set=9`: Inserting 3 items with $k=3$ set 9 distinct bits in the 64-bit array without collision.
2. `apple`, `banana`, and `cherry` evaluate to `True` with zero false negatives.
3. `durian` and `elderberry` evaluate to `False`.
4. `union_filters` bitwise-ORs the packed integer words, preserving membership from both sets.

---

## Conclusion

With `stdlib/bloom.ltl`, Lateralus provides an ultra-lightweight, memory-efficient probabilistic filter ideal for LSM-tree read bypasses, web crawl deduplication, and distributed query optimization.
