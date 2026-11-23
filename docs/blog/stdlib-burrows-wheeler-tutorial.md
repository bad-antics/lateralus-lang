# The Burrows-Wheeler Transform & LF-Mapping Inversion in Lateralus

## 1. Introduction & Executive Summary

In 1994, **Michael Burrows and David Wheeler** published a seminal technical report at Digital Equipment Corporation (DEC SRC) titled *"A Block-sorting Lossless Data Compression Algorithm"*. The core innovation—the **Burrows-Wheeler Transform (BWT)**—is widely regarded as one of the most elegant discoveries in computer science and information theory.

Unlike traditional dictionary-based compressors (e.g., LZ77, LZ78, DEFLATE/gzip), BWT does not compress data by itself. Instead, it computes a reversible permutation of a string such that characters with similar contexts are grouped into contiguous clusters. When piped into **Move-to-Front (MTF)** coding, **Run-Length Encoding (RLE)**, and **Huffman / Arithmetic coding**, BWT forms the heart of **bzip2**, achieving compression ratios rivaling the theoretical Shannon entropy limit.

Beyond data compression, BWT revolutionized computational biology. By augmenting the transformed text with succinct rank vectors, Paolo Ferragina and Giovanni Manzini (2000) created the **FM-Index**, which powers industry-standard sequence aligners like **Bowtie** and **BWA**, enabling billions of short DNA reads to be aligned against the 3-billion-base human genome in minutes.

This tutorial provides a complete mathematical derivation of the **LF-mapping property** and delivers a verified production implementation in Lateralus.

---

## 2. Theoretical Mechanics: Forward Transformation

Let $T = t_0 t_1 \dots t_{n-1}$ be a string of length $n$ over alphabet $\Sigma$, terminated by a unique sentinel character $\$$ that is lexicographically smaller than any character in $\Sigma$.

### 2.1 The Cyclic Rotation Matrix

Construct the $n \times n$ matrix $M$ whose rows consist of all $n$ cyclic shifts (rotations) of $T$:
$$M_{i} = T[i \dots n-1] \cdot T[0 \dots i-1], \quad 0 \le i < n$$

Sort the rows of $M$ in ascending lexicographical order to form matrix $M'$.

```
Example: T = "banana$" (n = 7)

All Cyclic Shifts (M):            Sorted Cyclic Shifts (M'):
  Row 0: banana$                     Row 0: $banana       (L[0] = a)
  Row 1: anana$b                     Row 1: a$banana      (L[1] = a)
  Row 2: nana$ba                     Row 2: ana$ban       (L[2] = n)
  Row 3: ana$ban                     Row 3: anana$b       (L[3] = b)
  Row 4: na$bana                     Row 4: banana$  <--- (Primary Index I = 4, L[4] = $)
  Row 5: a$banana                    Row 5: na$bana       (L[5] = a)
  Row 6: $banana                     Row 6: nana$ba       (L[6] = a)
```

### 2.2 Definitions: First Column $F$, Last Column $L$, and Primary Index $I$

- **Last Column ($L$)**: The output of the transform is string $L = M'[\cdot, n-1]$. In our example, $L = \text{"annb\$aa"}$.
- **Primary Index ($I$)**: The 0-based row index in $M'$ containing the original string $T$. Here, row 4 is `banana$`, so $I = 4$.
- **First Column ($F$)**: The first characters of the sorted rows $M'[\cdot, 0]$. Notice that $F$ is simply the characters of $L$ sorted in lexicographical order: $F = [\$, a, a, a, b, n, n]$.

---

## 3. The Mathematical Miracle: LF-Mapping & Lossless Inversion

How can $T$ be completely reconstructed given only $L$ and $I$? The answer lies in the **Last-to-First (LF) Mapping Property**.

### 3.1 Theorem (LF-Mapping Invariant)
*The $k$-th occurrence of character $c$ in the last column $L$ corresponds to the exact same text character as the $k$-th occurrence of character $c$ in the first column $F$.*

#### Proof:
1. In any cyclic rotation row $r = M'[r]$, the character $L[r] = M'[r, n-1]$ immediately precedes $F[r] = M'[r, 0]$ in the original cyclic text.
2. Consider two rows $r_1$ and $r_2$ that both end with the same character $c$, i.e., $L[r_1] = L[r_2] = c$.
3. When these two rows are cyclically shifted one position to the right, their first characters become $c$, followed by the remainder of rows $r_1$ and $r_2$.
4. Because row $r_1$ is lexicographically smaller than row $r_2$ ($r_1 < r_2$), the suffix following $c$ in row $r_1$ is lexicographically smaller than the suffix following $c$ in row $r_2$.
5. Therefore, when rows are sorted by their first character, row $r_1$ will precede row $r_2$ in the block of rows starting with character $c$ in column $F$.
6. Consequently, relative ordering among identical characters is strictly preserved between $L$ and $F$. $\blacksquare$

### 3.2 Reconstruction Algorithm

To invert BWT:
1. Let $C[c]$ be the number of characters in $L$ that are strictly smaller than $c$. (This marks the starting row index of character $c$ in $F$).
2. Let $\text{Rank}_L(c, i)$ denote the number of times character $c$ appears in $L[0 \dots i-1]$.
3. The LF-mapping function maps row $i$ in $L$ to its corresponding row in $F$:
   $$LF(i) = C[L[i]] + \text{Rank}_L(L[i], i)$$
4. Starting at $curr = I$, the character $L[curr]$ is the last character of the original text. Setting $curr \leftarrow LF(curr)$ steps backward one character at a time, reconstructing $T$ in reverse order in $O(n)$ steps.

---

## 4. Lateralus Implementation

```lateralus
// stdlib/burrows_wheeler.ltl
pub fn rot_cmp(text: str, i: int, j: int, n: int) -> int {
    let mut k = 0
    while k < n {
        let pos1 = (i + k) % n
        let pos2 = (j + k) % n
        let c1 = text[pos1]
        let c2 = text[pos2]
        if c1 < c2 {
            return -1
        }
        if c1 > c2 {
            return 1
        }
        k = k + 1
    }
    return 0
}

pub fn bwt_transform(text: str) -> dict {
    let mut res = {}
    let n = text.len()
    if n == 0 {
        res["transformed"] = ""
        res["primary_index"] = 0
        return res
    }

    let mut shifts = []
    let mut i = 0
    while i < n {
        shifts.push(i)
        i = i + 1
    }

    let mut p = 1
    while p < n {
        let key = shifts[p]
        let mut q = p - 1
        let mut moving = true
        while moving and q >= 0 {
            let prev = shifts[q]
            if rot_cmp(text, key, prev, n) < 0 {
                shifts[q + 1] = prev
                q = q - 1
            } else {
                moving = false
            }
        }
        shifts[q + 1] = key
        p = p + 1
    }

    let mut transformed = ""
    let mut primary_index = 0
    let mut r = 0
    while r < n {
        let shift = shifts[r]
        if shift == 0 {
            primary_index = r
        }
        let last_pos = (shift + n - 1) % n
        transformed = transformed + text[last_pos]
        r = r + 1
    }

    res["transformed"] = transformed
    res["primary_index"] = primary_index
    return res
}

pub fn bwt_inverse(transformed: str, primary_index: int) -> str {
    let n = transformed.len()
    if n == 0 {
        return ""
    }

    let mut counts = {}
    let mut rank = []
    let mut i = 0
    while i < n {
        let ch = transformed[i]
        let mut current_cnt = 0
        if contains(counts, ch) {
            current_cnt = counts[ch]
        }
        rank.push(current_cnt)
        counts[ch] = current_cnt + 1
        i = i + 1
    }

    let mut distinct_chars = keys(counts)
    let m = distinct_chars.len()
    let mut a = 1
    while a < m {
        let k = distinct_chars[a]
        let mut b = a - 1
        let mut moving = true
        while moving and b >= 0 {
            let prev = distinct_chars[b]
            if k < prev {
                distinct_chars[b + 1] = prev
                b = b - 1
            } else {
                moving = false
            }
        }
        distinct_chars[b + 1] = k
        a = a + 1
    }

    let mut c_offsets = {}
    let mut total_offset = 0
    let mut d = 0
    while d < m {
        let ch = distinct_chars[d]
        c_offsets[ch] = total_offset
        let cnt = counts[ch]
        total_offset = total_offset + cnt
        d = d + 1
    }

    let mut next_row = []
    let mut j = 0
    while j < n {
        let ch = transformed[j]
        let base_off = c_offsets[ch]
        let r_val = rank[j]
        next_row.push(base_off + r_val)
        j = j + 1
    }

    let mut reconstructed_chars = []
    let mut curr = primary_index
    let mut step = 0
    while step < n {
        let ch = transformed[curr]
        reconstructed_chars.push(ch)
        curr = next_row[curr]
        step = step + 1
    }

    let mut original = ""
    let mut idx = n - 1
    while idx >= 0 {
        original = original + reconstructed_chars[idx]
        idx = idx - 1
    }

    return original
}
```

---

## 5. Complexity & Compression Metrics

| Phase | Time Complexity | Space Complexity | Description |
| :--- | :--- | :--- | :--- |
| **Rotation Sorting** | $O(n \log n)$ (with SA-IS: $O(n)$) | $O(n)$ | Lexicographical order of cyclic shifts |
| **Column Extraction** | $O(n)$ | $O(n)$ | Gathers last column $L$ and records $I$ |
| **LF Array Construction** | $O(n + |\Sigma| \log |\Sigma|)$ | $O(n + |\Sigma|)$ | Computes $C[c]$ offsets and rank vectors |
| **Inversion (Decoding)** | $O(n)$ | $O(n)$ | Backward walk over $n$ steps |

---

## 6. Real-World Applications: The bzip2 Pipeline & FM-Index

### 6.1 The bzip2 Compaction Architecture
BWT dramatically reduces zero-order empirical entropy by grouping contextually identical bytes:
$$\text{Raw Text} \xrightarrow{\text{BWT}} \text{Clustered } L \xrightarrow{\text{MTF}} \text{Small Integers} \xrightarrow{\text{RLE}} \text{Runs of Zeros} \xrightarrow{\text{Huffman}} \text{Compressed File}$$

### 6.2 The FM-Index in Computational Genomics
Given a human reference genome of 3.2 billion base pairs, the FM-Index stores $L$ along with sampled rank checkpoints. Querying whether a 100-bp read occurs in the genome requires only 100 backward LF-steps, locating all matches in sub-millisecond time without ever decompressing the reference.

---

## 7. Conclusion

The Burrows-Wheeler Transform stands as a masterwork of algorithmic elegance. Through cyclic permutation and the invariant of LF-mapping, it turns non-local context dependencies into contiguous runs of characters, unlocking near-optimal lossless compression and hyperscale genomic search.
