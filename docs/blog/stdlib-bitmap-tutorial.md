# High-Density Bitmaps and BitSets in Lateralus: Word-Level Parallelism, Bit Manipulation, and Cache-Conscious Set Arithmetic

In systems programming, database indexing (e.g., Roaring bitmaps, inverted postings lists), garbage collector mark-and-sweep phases, and network routing filters, tracking dense sets of boolean flags or integer IDs is a fundamental primitive.

Using dynamic arrays of booleans or hash tables incurs massive memory overhead:
- A generic `bool` or heap object often consumes 8 to 64 bytes per flag due to object headers and word alignment.
- A **Bitmap (BitSet)** packs 32 booleans into a single 32-bit integer word (or 64 into a 64-bit word), achieving a **$32\times$ to $64\times$ memory reduction** and keeping millions of flags inside the CPU L1 data cache.
- Furthermore, bitwise operations (`&`, `|`, `^`) allow performing set intersection, union, and symmetric difference on 32 elements simultaneously in a **single CPU instruction cycle**.

In this tutorial, we implement, benchmark, and mathematically verify a high-density Bitmap engine in Lateralus.

---

## 1. Mathematical Mapping & Invariants

Let an arbitrary non-negative integer ID or bit position be $i \in [0, N-1]$. Assuming a word size of $W = 32$ bits:

1. **Word Index**:
   $$w = \lfloor i / 32 \rfloor$$
2. **Bit Offset**:
   $$b = i \pmod{32}$$
3. **Bit Mask**:
   $$\text{mask} = 1 \ll b$$

### Fundamental Operations

- **Set Bit ($i \in S$)**:
  $$\text{words}[w] \leftarrow \text{words}[w] \mid \text{mask}$$
- **Test Bit ($i \in S?$)**:
  $$\text{present} \leftarrow (\text{words}[w] \ \& \ \text{mask}) \neq 0$$
- **Clear Bit ($S \setminus \{i\}$)**:
  $$\text{if } (\text{words}[w] \ \& \ \text{mask}) \neq 0 \implies \text{words}[w] \leftarrow \text{words}[w] \oplus \text{mask}$$
- **Toggle Bit ($S \vartriangle \{i\}$)**:
  $$\text{words}[w] \leftarrow \text{words}[w] \oplus \text{mask}$$

---

## 2. Word-Level Parallel Set Arithmetic

Instead of iterating element-by-element across sets, bitmaps operate at the word level:

- **Set Union ($A \cup B$)**:
  $$\text{Union}[k] = A[k] \mid B[k]$$
- **Set Intersection ($A \cap B$)**:
  $$\text{Intersect}[k] = A[k] \ \& \ B[k]$$

Both operations execute in $O(N / 32)$ time complexity, achieving 32-way SIMD-style parallel evaluation.

---

## 3. The Lateralus Implementation

### 3.1 Allocation and Basic Mutations

```lateralus
fn bitmap_create(capacity: int) -> list {
    let mut words = [];
    let mut num_words = capacity / 32;
    if capacity % 32 != 0 {
        num_words = num_words + 1;
    }
    let mut i = 0;
    while i < num_words {
        words = words + [0];
        i = i + 1;
    }
    return words;
}

fn bitmap_set(words: list, bit_idx: int) -> list {
    let mut res = words;
    let w_idx = bit_idx / 32;
    let b_pos = bit_idx % 32;
    let mask = 1 << b_pos;
    res[w_idx] = res[w_idx] | mask;
    return res;
}

fn bitmap_test(words: list, bit_idx: int) -> bool {
    let w_idx = bit_idx / 32;
    let b_pos = bit_idx % 32;
    let mask = 1 << b_pos;
    return (words[w_idx] & mask) != 0;
}
```

### 3.2 Population Count (Hamming Weight)

The Hamming weight counts the total number of non-zero bits set across the bitmap:

```lateralus
fn word_popcount(w: int) -> int {
    let mut count = 0;
    let mut val = w;
    while val > 0 {
        count = count + (val & 1);
        val = val >> 1;
    }
    return count;
}

fn bitmap_popcount(words: list) -> int {
    let mut total = 0;
    let mut i = 0;
    while i < len(words) {
        total = total + word_popcount(words[i]);
        i = i + 1;
    }
    return total;
}
```

---

## 4. Verification and Execution

Validate the implementation against compiler checks and pytest:

```powershell
# 1. Run the interactive tutorial example
lateralus_lang run examples/bitmap_tutorial.ltl

# 2. Run the compiler verification test suite
lateralus_lang check tests/stdlib_bitmap_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus Dense Bitmap & BitSet Engine Demo ===
Initialized 64-bit BitSet (Words allocated: 2)
Active flags set at indices: [7, 19, 42, 63]
Hamming Weight (Population Count): 4
Membership query test(42) -> true, test(10) -> false: Verified!
Cleared flag 19 -> Remaining active flags: 3

Bitmap operations completed successfully with 100% precision!
```

---

## 5. Summary

Dense bitmaps demonstrate how low-level bit manipulation and word-level parallelism deliver both extreme space efficiency and ultra-fast set operations in Lateralus.
