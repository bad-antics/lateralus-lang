# Columnar Compression and Dictionary Encoding with Lateralus `stdlib/dict_encoding.ltl`

Modern analytical databases (ClickHouse, DuckDB) and columnar storage formats (Apache Parquet, Apache Arrow) achieve unprecedented query speeds and compression ratios by storing table attributes vertically rather than horizontally. 

When a column contains low-cardinality repetitive data—such as HTTP status codes, ISO country codes, cloud regions, or device categories—storing full strings repeatedly in memory and on disk wastes bandwidth and destroys CPU cache locality.

Lateralus provides a high-performance, standard library dictionary encoding implementation in `stdlib/dict_encoding.ltl`. This tutorial covers how dictionary encoding works, the mathematics of index bit-width compression, deterministic first-seen symbol ordering, and lossless data reconstruction.

---

## 1. What is Dictionary Encoding?

Dictionary Encoding converts an uncompressed array of arbitrary values into two separate, compact data structures:

1. **`dictionary`**: A dense, deduplicated array containing each unique symbol in its **first-seen order**.
2. **`indices`**: A compact sequence of integer pointers of identical length to the original array, where each element indexes into the `dictionary`.

```text
Original Column (12 elements, ~144 bytes):
["us-east-1", "us-west-2", "eu-central-1", "us-east-1", "us-west-2", "us-east-1", ...]

Dictionary (4 elements, ~48 bytes):
0: "us-east-1"
1: "us-west-2"
2: "eu-central-1"
3: "ap-southeast-1"

Indices (12 elements @ 2 bits each = 24 bits / 3 bytes):
[0, 1, 2, 0, 1, 0, 3, 2, 0, 0, 1, 3]
```

Total storage drops from **144 bytes** down to **51 bytes** (~65% reduction), while transforming costly string comparisons during filtering and aggregation into blazing fast, branchless integer lookups.

---

## 2. API Reference: `stdlib/dict_encoding.ltl`

The module exposes four core functions:

### `dict_encoding.encode(values: list) -> map`
Scans `values` in linear time $O(N)$ and constructs a dictionary map:
* `enc["dictionary"]`: List of unique values in first-seen sequence.
* `enc["indices"]`: List of integer indices corresponding to the positions in `dictionary`.

### `dict_encoding.decode(enc: map) -> list`
Reconstructs the original sequence by mapping `enc["indices"]` back to `enc["dictionary"][idx]`. Guarantees lossless $O(N)$ reconstruction.

### `dict_encoding.cardinality(enc: map) -> int`
Returns the count of distinct unique symbols $C = \text{len}(\text{dictionary})$.

### `dict_encoding.index_bit_width(enc: map) -> int`
Calculates the minimum bit-width required to store indices in compact bit-packed columnar blocks:

$$\text{bit\_width} = \max\left(1, \lceil \log_2(C) \rceil\right)$$

* For $C \le 2$: 1 bit per index
* For $C \in [3, 4]$: 2 bits per index
* For $C \in [5, 8]$: 3 bits per index
* For $C \in [9, 16]$: 4 bits per index

---

## 3. Practical Example: Compressing Cloud Telemetry

The companion executable `examples/dict_encoding_tutorial.ltl` illustrates an end-to-end pipeline:

```lateralus
import dict_encoding

pub fn main() {
    let regions = [
        "us-east-1", "us-west-2", "eu-central-1", "us-east-1",
        "us-west-2", "us-east-1", "ap-southeast-1", "eu-central-1",
        "us-east-1", "us-east-1", "us-west-2", "ap-southeast-1"
    ]

    // 1. Encode column
    let enc = dict_encoding.encode(regions)
    print("Dictionary: " + str(enc["dictionary"]))
    print("Indices:    " + str(enc["indices"]))

    // 2. Compute metrics
    let card = dict_encoding.cardinality(enc)
    let bw   = dict_encoding.index_bit_width(enc)
    print("Cardinality: " + str(card))        // 4
    print("Bit width:   " + str(bw) + " bits") // 2

    // 3. Lossless reconstruction
    let restored = dict_encoding.decode(enc)
    print("Round-trip verified: " + str(restored == regions))
}
```

Running this example produces:

```text
=== Lateralus Columnar Dictionary Encoding Tutorial ===
Total rows in column: 12
Dictionary entries (first-seen order):
  [0] -> us-east-1
  [1] -> us-west-2
  [2] -> eu-central-1
  [3] -> ap-southeast-1
Compact index stream:
  [0, 1, 2, 0, 1, 0, 3, 2, 0, 0, 1, 3]
Cardinality (unique symbols): 4
Index bit-width (ceil(log2(N))): 2 bits per row
Estimated index storage for 12 rows: 3 bytes
Decoding verified: true
PASS: Lossless reconstruction 100% matches original dataset!
=== Columnar dictionary encoding completed successfully ===
```

---

## 4. Verification and Pinned Test Vectors

To ensure absolute determinism across all targets (bytecode VM, native C99, JavaScript ES2022, WebAssembly), `tests/stdlib_dict_encoding_tutorial.ltl` tests five key invariants:

1. **Basic Round-Trip Invariant**: $\text{decode}(\text{encode}(X)) \equiv X$ for arbitrary lists.
2. **First-Seen Determinism**: Index zero is always assigned to the element appearing first in the input stream.
3. **Edge Case Safety**: Graceful behavior on empty lists `[]`, single-element arrays `["x"]`, and monolithic duplicate arrays.
4. **Logarithmic Bit-Width Scaling**: Exact ceiling bit-width transitions across power-of-two cardinality thresholds.
5. **Poly-Type Support**: Transparent encoding of numeric primitives, strings, and identifiers.

---

## 5. Summary

With `stdlib/dict_encoding.ltl`, Lateralus applications can ingest large streams of tabular data, eliminate duplicate allocations, and generate storage-efficient vectors ready for Arrow IPC serialization and Parquet packaging.
