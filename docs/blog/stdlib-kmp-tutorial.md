# Mastering Knuth-Morris-Pratt (KMP) in Lateralus: LPS Precomputation, Backtrack-Free Matching, and Stream Search

Naive substring search algorithms compare a pattern against a target text character by character. When a mismatch occurs, the naive algorithm resets the text pointer and restarts comparisons from the next character, degrading performance to $O(N \times M)$ on adversarial inputs (such as repetitive binary headers or genomic sequences).

The **Knuth-Morris-Pratt (KMP) Algorithm** (developed by Donald Knuth, Vaughan Pratt, and James H. Morris) achieves optimal **$O(N + M)$** time complexity. By precomputing a **Longest Prefix Suffix (LPS)** table (also known as the $\pi$ function), the algorithm determines exactly how many pattern characters can be safely skipped upon a mismatch, guaranteeing that the main text pointer **never backtracks**.

In this tutorial, we implement, analyze, and verify KMP string searching natively in Lateralus.

---

## 1. The Longest Prefix Suffix (LPS) Array

The LPS table records the length of the longest proper prefix of $P[0 \dots i]$ that is also a suffix of $P[0 \dots i]$:

- For pattern `"ABCDABD"`:
  - `"A"` $\to 0$
  - `"AB"` $\to 0$
  - `"ABC"` $\to 0$
  - `"ABCD"` $\to 0$
  - `"ABCDA"` $\to 1$ (prefix `"A"` matches suffix `"A"`)
  - `"ABCDAB"` $\to 2$ (prefix `"AB"` matches suffix `"AB"`)
  - `"ABCDABD"` $\to 0$

$$\text{LPS}(\text{"ABCDABD"}) = [0, 0, 0, 0, 1, 2, 0]$$

```lateralus
fn compute_lps(pattern: string) -> list {
    let p_len = len(pattern);
    if p_len == 0 {
        return [];
    }
    let mut lps = [0];
    let mut prev_lps = 0;
    let mut i = 1;

    while i < p_len {
        let ch_i = slice(pattern, i, i + 1);
        let ch_prev = slice(pattern, prev_lps, prev_lps + 1);

        if ch_i == ch_prev {
            prev_lps = prev_lps + 1;
            lps.append(prev_lps);
            i = i + 1;
        } else {
            if prev_lps != 0 {
                prev_lps = lps[prev_lps - 1];
            } else {
                lps.append(0);
                i = i + 1;
            }
        }
    }
    return lps;
}
```

---

## 2. Linear Backtrack-Free Searching

During scanning, index $i$ in text never decrements:
- On match: advance both $i$ and $j$. If $j == \text{length}$, record match index $i - j$.
- On mismatch: if $j > 0$, shift pattern index $j = \text{LPS}[j - 1]$ without rolling back $i$. If $j == 0$, increment $i$.

Because $i$ monotonically increases, search runtime is strictly bounded by $O(N)$.

---

## 3. Real-World Security Log Scanning

In security monitoring and Deep Packet Inspection (DPI), stream buffers cannot be rewound. KMP enables single-pass scanning for exploit payloads directly off network sockets.

See `examples/kmp_tutorial.ltl` for a runnable demonstration scanning access logs for injection signatures.

---

## 4. End-to-End Verification with Canonical Golden Vectors

We assert compliance against standard computer science benchmarks:
- **Canonical LPS vector**: `"ABCDABD"` yields `[0, 0, 0, 0, 1, 2, 0]`.
- **Repetitive pattern vector**: `"AAAA"` yields `[0, 1, 2, 3]`.
- **Exact match benchmarks**: Substring search correctly identifying offset 15 in `"ABC ABCDAB ABCDABCDABDE"`.

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/kmp_tutorial.ltl
python -m lateralus_lang check tests/stdlib_kmp_tutorial.ltl
pytest tests/test_compiler.py
```
