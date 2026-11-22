# Run-Length Encoding (RLE) in Lateralus: Lossless Run Aggregation, Worst-Case Complexity, and Raster Graphics Compression

In data compression and systems programming, **Run-Length Encoding (RLE)** is one of the earliest and most intuitive lossless compression techniques. First utilized in the 1960s for television signal transmission, RLE subsequently became standard in raster image file formats (such as PCX, BMP, TIFF, and Apple PackBits) and fax transmission (ITU-T T.4).

RLE replaces consecutive repeated occurrences of the same data value (a "run") with a single value and a count. It achieves near-instantaneous $O(N)$ linear-time compression with zero lookahead overhead.

In this tutorial, we implement, benchmark, and mathematically verify a complete Run-Length Encoding and Decoding engine in Lateralus.

---

## 1. Algorithmic Principles & Complexity

Let an uncompressed sequence $X$ have length $N$. RLE partitions $X$ into $K$ runs:

$$X = \underbrace{s_1 s_1 \dots s_1}_{c_1 \text{ times}} \ \underbrace{s_2 s_2 \dots s_2}_{c_2 \text{ times}} \ \dots \ \underbrace{s_K s_K \dots s_K}_{c_K \text{ times}}$$

Where $c_i \ge 1$, $s_i \neq s_{i+1}$, and $\sum_{i=1}^K c_i = N$.

### Best-Case vs. Worst-Case Analysis

1. **Best-Case (Uniform Stream)**:
   - Input: $N$ identical symbols (e.g., `"ZZZZZZZZZZ"` where $N=10$).
   - Output: 1 run `[[10, "Z"]]`.
   - Compression Ratio: $O(1)$ space, achieving maximum bandwidth savings.
2. **Worst-Case (Non-Repeating Stream)**:
   - Input: $N$ distinct or alternating symbols (e.g., `"ABCDEF"`).
   - Output: $N$ runs with $c_i = 1$.
   - Note: In naive pair storage, storing `(1, s)` for each symbol can double memory usage. Practical formats like Apple PackBits use a signed header byte where positive values denote repeated runs and negative values denote raw literal copies.

---

## 2. Invariant: Lossless Roundtrip Equivalence

The fundamental invariant of any lossless compression scheme is the identity property:

$$\operatorname{decode}(\operatorname{encode}(X)) = X$$

In Lateralus, our test suite verifies this invariant across uniform runs, mixed workloads, single-character strings, and worst-case non-repeating inputs:

```lateralus
let runs = rle_encode(payload);
let restored = rle_decode(runs);
assert(restored == payload); // Proves lossless preservation!
```

---

## 3. The Lateralus Implementation

### 3.1 Single-Pass Linear Encoder

```lateralus
fn rle_encode(text: string) -> list {
    let mut runs = [];
    let n = len(text);
    if n == 0 {
        return runs;
    }

    let mut current_char = slice(text, 0, 1);
    let mut current_count = 1;
    let mut i = 1;

    while i < n {
        let ch = slice(text, i, i + 1);
        if ch == current_char {
            current_count = current_count + 1;
        } else {
            runs = runs + [[current_count, current_char]];
            current_char = ch;
            current_count = 1;
        }
        i = i + 1;
    }
    runs = runs + [[current_count, current_char]];
    return runs;
}
```

### 3.2 Streaming Run Expander / Decoder

```lateralus
fn rle_decode(runs: list) -> string {
    let mut result = "";
    let mut i = 0;
    while i < len(runs) {
        let run = runs[i];
        let mut count = run[0];
        let ch = run[1];
        while count > 0 {
            result = result + ch;
            count = count - 1;
        }
        i = i + 1;
    }
    return result;
}
```

---

## 4. Verification and Execution

Run compiler checks and the validation test suite:

```powershell
# 1. Run interactive tutorial demo
lateralus_lang run examples/rle_tutorial.ltl

# 2. Run compiler check and unit test suite
lateralus_lang check tests/stdlib_rle_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus Run-Length Encoding (RLE) Pipeline Demo ===
Original Raw Payload: "WWWWWWAAAAAABBBCCCD" (19 characters)
Computed Runs: [[6, "W"], [6, "A"], [3, "B"], [3, "C"], [1, "D"]]
Packed RLE Tokenstream: "6W6A3B3C1D" (10 characters)
Decompressed Payload: "WWWWWWAAAAAABBBCCCD"

RLE compression and lossless decompression verified 100% faithful!
```

---

## 5. Summary

Run-Length Encoding proves that simple, linear-time algorithms can dramatically compress redundant data without algorithmic complexity. In Lateralus, string slicing and list operations provide an expressive, clean syntax for building robust streaming compression pipelines.
