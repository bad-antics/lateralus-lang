---
title: "Linear String Preprocessing: Implementing Gusfield's Z-Algorithm in Lateralus"
description: "A comprehensive guide to implementing Dan Gusfield's linear O(n) Z-Algorithm in Lateralus for prefix-box exact pattern matching and string periodicity detection."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "strings", "pattern-matching", "genomics", "standard-library"]
---

# Linear String Preprocessing: Implementing Gusfield's Z-Algorithm in Lateralus

In computational genomics (detecting microsatellite tandem repeats), text processing engines (exact substring search), and compiler lexers, understanding the internal prefix structure of a string is fundamental.

While the Knuth-Morris-Pratt (KMP) algorithm computes failure functions ($\pi$-tables) based on longest proper prefix-suffixes, **Dan Gusfield's Z-Algorithm** (1997, *"Algorithms on Strings, Trees, and Sequences"*) computes the fundamental string preprocessing values directly:
- **Definition**: For a string $S$ of length $n$, the value $Z[i]$ is the length of the longest substring starting at $S[i]$ that matches a prefix of $S$:
  $$Z[i] = \max \{ k \mid S[0 \dots k-1] = S[i \dots i+k-1] \}$$
- **Linear Complexity**: Runs in strictly $O(n)$ time and $O(n)$ space.
- **Pattern Matching**: Solves exact pattern search in $O(n + m)$ without DFA tables by running directly on $P + \text{"#"} + T$.

---

## 1. The $[L, R]$ Matching Box Invariant

The core efficiency of the Z-Algorithm arises from maintaining a **matching box interval $[L, R]$**, representing the rightmost segment of $S$ that matches a prefix of $S$:

$$S[L \dots R] = S[0 \dots R - L]$$

As index $i$ progresses from $1$ to $n - 1$:

### 1.1 Case 1: Outside the Current Box ($i > R$)
No prior prefix match extends to $i$. We perform direct character-by-character comparisons between $S[i \dots]$ and $S[0 \dots]$. If a match of length $k > 0$ is found, we establish a new matching box $[L, R] = [i, i + k - 1]$.

### 1.2 Case 2: Inside the Current Box ($i \le R$)
Since $S[L \dots R]$ matches $S[0 \dots R - L]$, the character at $S[i]$ corresponds directly to the character at prefix index:
$$k = i - L$$

Two sub-cases emerge based on the precomputed value $Z[k]$:

1. **Subcase 2a ($Z[k] < R - i + 1$)**:
   The match starting at $S[k]$ does not reach the right boundary of the box. Due to identity within $[L, R]$, the match starting at $S[i]$ cannot extend further. Thus:
   $$Z[i] = Z[k] \quad (\text{resolved in } O(1))$$

2. **Subcase 2b ($Z[k] \ge R - i + 1$)**:
   The match starting at $S[k]$ extends to or past the right boundary $R$. We know $S[i \dots R]$ matches $S[0 \dots R - i]$. We set $L = i$ and continue direct comparisons starting past $R$, expanding $R$ to the right.

### 1.3 Amortized Linear Complexity Proof
Each character comparison either:
- Fails (occurring at most once per index $i$, contributing $O(n)$ total failed checks), or
- Succeeds and advances $R$ strictly to the right ($R$ starts at $0$ and cannot exceed $n - 1$).

Hence, the total number of character comparisons is bounded by $2n$, proving strictly linear $O(n)$ execution time.

---

## 2. Lateralus Implementation

Here is the clean implementation of `stdlib/z_algorithm.ltl`:

```lateralus
pub fn compute_z(chars, n) {
    let z = dict()
    let idx = 0
    while idx < n {
        z[idx] = 0
        idx = idx + 1
    }
    if n == 0 {
        return z
    }
    z[0] = n

    let l = 0
    let r = 0
    let i = 1
    while i < n {
        if i <= r {
            let k = i - l
            let remaining = r - i + 1
            if z[k] < remaining {
                z[i] = z[k]
            } else {
                l = i
                while r < n {
                    if chars[r] != chars[r - l] {
                        break
                    }
                    r = r + 1
                }
                z[i] = r - l
                r = r - 1
            }
        } else {
            l = i
            r = i
            while r < n {
                if chars[r] != chars[r - l] {
                    break
                }
                r = r + 1
            }
            z[i] = r - l
            r = r - 1
        }
        i = i + 1
    }
    return z
}

pub fn z_pattern_match(pattern, pat_len, text, text_len) {
    let n = pat_len + 1 + text_len
    let combined = dict()

    let i = 0
    while i < pat_len {
        combined[i] = pattern[i]
        i = i + 1
    }
    combined[pat_len] = "#"

    let j = 0
    while j < text_len {
        combined[pat_len + 1 + j] = text[j]
        j = j + 1
    }

    let z = compute_z(combined, n)
    let matches = dict()
    matches["count"] = 0

    let k = pat_len + 1
    while k < n {
        if z[k] == pat_len {
            let match_idx = k - (pat_len + 1)
            let curr_cnt = matches["count"]
            matches[curr_cnt] = match_idx
            matches["count"] = curr_cnt + 1
        }
        k = k + 1
    }
    return matches
}

pub fn z_find_smallest_period(chars, n) {
    if n <= 1 {
        return n
    }
    let z = compute_z(chars, n)
    let p = 1
    while p < n {
        if n % p == 0 {
            if z[p] == n - p {
                return p
            }
        }
        p = p + 1
    }
    return n
}
```

---

## 3. Practical Application: Genomic Tandem Repeat & Primer Detection

Microsatellite DNA sequences (Short Tandem Repeats / STRs) consist of repeating nucleotide motifs (such as `"CAG"` repeats implicated in Huntington's disease). The Z-Algorithm identifies both motif periodicities and exact primer matches in linear time:

```lateralus
pub fn run_dna_tandem_repeat_pipeline() {
    // Genomic DNA Sequence: "CAGCAGCAGCAG" (length 12)
    let dna = dict()
    // ... load nucleotides ...

    // Automatically detects the smallest repeating unit: length 3 ("CAG")
    let tandem_unit_len = z_find_smallest_period(dna, 12)

    // Query Primer Sequence "AGCA" across chromosome
    let primer = dict()
    // ... load primer ...
    let primer_matches = z_pattern_match(primer, 4, dna, 12)
}
```

---

## 4. Verification & Testing

The verification test suite in `tests/stdlib_z_algorithm_tutorial.ltl` validates:
1. **Empty String Invariance**: Safely computes zero-length input.
2. **Canonical Prefix Vector Matching**: On `"aabzaab"`, asserts exact vector `[7, 1, 0, 0, 3, 1, 0]`.
3. **Exact Pattern Matching**: Locates disjoint and overlapping occurrences in linear time.
4. **Periodicity Determination**: Accurately classifies periodic strings (`"abcabcabc"` $\to 3$), homogeneous strings (`"aaaa"` $\to 1$), and aperiodic sequences.

Execute the test suite with:

```bash
lateralus check tests/stdlib_z_algorithm_tutorial.ltl
lateralus check examples/z_algorithm_tutorial.ltl
pytest tests/test_compiler.py
```
