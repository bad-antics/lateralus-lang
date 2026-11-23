# Dictionary Encoding for Columnar Data Compression: Invariants, Bit-Width Heuristics, and Applications in Lateralus

## 1. Introduction & Theoretical Foundations

In modern analytical databases (OLAP), data warehouses, and streaming telemetry pipelines (such as ClickHouse, DuckDB, Apache Parquet, and Apache Arrow), storage bandwidth and in-memory cache locality dominate execution throughput. Analytical query workloads typically scan billions of rows across narrow subsets of columns.

When columns contain repeated strings or scalar categories with low cardinality—such as HTTP methods (`GET`, `POST`), status codes (`200_OK`, `404_NOT_FOUND`), ISO country codes (`US`, `DE`), or status flags (`ACTIVE`, `PENDING`)—storing raw strings sequentially introduces massive redundancy, inflates memory footprints, and bottlenecks memory bus bandwidth.

**Dictionary Encoding** (also known as category indexing or dictionary compression) resolves this inefficiency by decoupling the unique values from their repetition. It decomposes a column into two compact components:
1. **Dictionary (Codebook)**: A deduplicated array containing each unique value exactly once.
2. **Indices Array**: A compact integer array of the same length as the original column, where each integer references the dictionary position of the corresponding row value.

This encoding forms the bedrock of Parquet's `PLAIN_DICTIONARY` page format and Arrow's `DictionaryArray` layout.

---

## 2. Mathematical Foundations & Entropy Reduction

### Shannon Entropy and Bit-Width Derivation
Let a column $V = [v_1, v_2, \dots, v_n]$ consist of $n$ elements drawn from an alphabet of distinct values $\Sigma = \{s_1, s_2, \dots, s_C\}$, where $C = |\Sigma|$ represents the column **cardinality**.

Instead of storing each entry as an arbitrary variable-length byte sequence with average byte length $\bar{L}$, each element can be represented as an index $k \in \{0, 1, \dots, C-1\}$. The minimum integer bit-width $w$ necessary to address all $C$ distinct dictionary slots is:
$$w = \begin{cases} 1 & \text{if } C \le 1 \\ \lceil \log_2 C \rceil & \text{if } C > 1 \end{cases}$$

Lateralus implements this exact logarithmic bit-width calculation in `stdlib/dict_encoding.ltl`:
```lateralus
pub fn index_bit_width(enc: map) -> int {
    let n = len(enc["dictionary"])
    if n <= 1 { return 1 }
    let bits = 0
    let v = n - 1
    while v > 0 { v = v >> 1; bits = bits + 1 }
    return bits
}
```

### Storage Complexity & Compression Ratio
Consider a telemetry column of $n = 1,000,000$ HTTP status strings with average length $\bar{L} = 16$ bytes and cardinality $C = 4$ (`200_OK`, `304_NOT_MODIFIED`, `404_NOT_FOUND`, `500_INTERNAL_SERVER_ERROR`).

1. **Uncompressed Raw Representation**:
   $$S_{\text{raw}} = n \cdot \bar{L} = 1,000,000 \times 16\text{ bytes} \approx 16.0\text{ MB}$$
2. **Dictionary Encoded Representation**:
   - Dictionary table: $4 \times 16\text{ bytes} = 64\text{ bytes}$.
   - Indices array: $C=4 \implies w = \lceil \log_2 4 \rceil = 2\text{ bits}$ per row.
   - Indices memory:
     $$S_{\text{indices}} = \frac{1,000,000 \times 2\text{ bits}}{8\text{ bits/byte}} = 250,000\text{ bytes} \approx 250\text{ KB}$$
   - Total encoded footprint:
     $$S_{\text{encoded}} = 64\text{ bytes} + 250\text{ KB} \approx 250.06\text{ KB}$$

**Net Data Reduction**: A compression ratio exceeding **$64 \times$** ($>98.4\%$ space savings), enabling entire million-row columns to reside permanently within CPU L2/L3 caches.

---

## 3. Algorithmic Architecture in Lateralus

Lateralus implements dictionary encoding in `stdlib/dict_encoding.ltl` with strict $O(n)$ time complexity and zero loss:

### Single-Pass First-Seen Encoding (`encode`)
1. Iterates over input values $v_i$.
2. Maintains a reverse index map $\text{dict\_idx}: \text{str}(v) \to \text{int}$.
3. If $v_i$ is novel, appends $v_i$ to `dictionary` at index $|\text{dictionary}|$, recording its position in $\text{dict\_idx}$.
4. Appends the index to `indices`.
5. Returns a structured map containing `dictionary` and `indices`.

### Deterministic Lossless Decoding (`decode`)
Given an encoded dictionary map:
$$v_i = \text{dictionary}[\text{indices}[i]]$$
Iterates over `indices` and performs direct vector lookups into `dictionary`, reconstructing the exact original column without floating-point drift or data degradation:
$$\text{decode}(\text{encode}(V)) \equiv V$$

---

## 4. Lateralus `stdlib/dict_encoding.ltl` API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `encode(values: list)` | `(list) -> map` | Compresses column into `{"dictionary": list, "indices": list}` in first-seen order. |
| `decode(enc: map)` | `(map) -> list` | Reconstructs the original uncompressed column from dictionary and indices. |
| `index_bit_width(enc: map)` | `(map) -> int` | Calculates minimum bits required per index: $\lceil \log_2(C) \rceil$ (minimum 1 bit). |
| `cardinality(enc: map)` | `(map) -> int` | Returns the total count of distinct dictionary entries ($C = |\text{dictionary}|$). |

---

## 5. Practical Implementation & Verification

### Executing the Runnable Example
An end-to-end telemetry compression example is provided in `examples/dict_encoding_tutorial.ltl`:
```shell
$ python -m lateralus_lang check examples/dict_encoding_tutorial.ltl
✓ examples/dict_encoding_tutorial.ltl: OK
```

The example demonstrates:
- Columnar encoding of web server access records.
- Inspecting cardinality and index bit-width.
- Evaluating memory savings.
- Verifying exact round-trip reconstruction equality.

### Pinned Golden Test Vectors
The companion test suite `tests/stdlib_dict_encoding_tutorial.ltl` verifies:
- Empty array edge case handling ($\text{cardinality} = 0, \text{indices} = []$).
- Monochromatic columns ($C = 1 \implies \text{bit\_width} = 1$).
- Binary domain verification ($C = 2 \implies \text{bit\_width} = 1$).
- First-seen dictionary ordering preservation.
- Logarithmic bit-width scaling across powers of two ($C=8 \implies 3\text{ bits}$, $C=9 \implies 4\text{ bits}$).
- Full round-trip identity assertions across all test cases.

Validate the test suite with the Lateralus compiler:
```shell
$ python -m lateralus_lang check tests/stdlib_dict_encoding_tutorial.ltl
✓ tests/stdlib_dict_encoding_tutorial.ltl: OK
```
