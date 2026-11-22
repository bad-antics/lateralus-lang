# Manacher's Algorithm Tutorial: Linear $O(n)$ Longest Palindromic Substring

## Overview

Finding the longest palindromic substring in a sequence of characters is a fundamental problem in string theory, bioinformatics, and natural language processing. A naive brute-force search evaluates all $O(n^2)$ substrings, leading to $O(n^3)$ or $O(n^2)$ time with expand-around-center approaches.

In 1975, Glenn K. Manacher discovered a linear time algorithm that finds the longest palindromic substring in strictly **$O(n)$ time and $O(n)$ auxiliary space**.

In computational genomics and biological sequence analysis, palindromic structures represent:
- **Inverted Repeats and Hairpin Loops**: Essential secondary structures in single-stranded RNA and DNA transcription termination.
- **Restriction Enzyme Recognition Sites**: Endonucleases cleaving DNA at specific palindromic motifs (e.g. EcoRI `GAATTC`).
- **CRISPR Direct Repeats**: Clustered Regularly Interspaced Short Palindromic Repeats utilized in gene editing systems.

---

## Algorithm Mechanics

Manacher's algorithm solves two primary hurdles:
1. **Even vs Odd Length Palindromes**: Even palindromes have their center between characters, while odd palindromes have their center on a character.
2. **Redundant Character Comparisons**: Overlapping palindromes recompute characters already examined.

### 1. Interleaving with Delimiters

To treat even and odd length palindromes uniformly, the original string $s$ is padded with a unique delimiter `#` between every character, flanked by start `^` and end `$` sentinels:
$$\text{"racecar"} \longrightarrow \text{"\textasciicircum\#r\#a\#c\#e\#c\#a\#r\#\$"}$$
$$\text{"noon"} \longrightarrow \text{"\textasciicircum\#n\#o\#o\#n\#\$"}$$

Every palindrome in the transformed string $t$ has an **odd length** centered on a specific index $i$, and its radius $P[i]$ in $t$ matches the exact length of the original palindrome in $s$.

### 2. Exploiting Symmetry Around Centers

The algorithm maintains:
- $C$: The center of the palindrome with the rightmost boundary discovered so far.
- $R$: The right boundary of this palindrome ($R = C + P[C]$).

For each current index $i > C$:
- The mirror position of $i$ with respect to center $C$ is:
  $$i' = 2C - i$$
- If $i < R$, the palindrome centered at $i$ is initially at least as large as the palindrome at $i'$, bounded by the remaining distance to $R$:
  $$P[i] = \min(P[i'], R - i)$$
- The algorithm then attempts to expand around $i$ only beyond the boundary $R$, incrementally increasing $P[i]$.
- Whenever $i + P[i] > R$, $C$ and $R$ are updated:
  $$C \leftarrow i, \quad R \leftarrow i + P[i]$$

Because $R$ only advances monotonically from left to right, character comparisons never regress, yielding strictly **$O(n)$ linear time complexity**.

---

## Lateralus Implementation

```lateralus
fn manacher_preprocess(s: str) -> str {
    let n = len(s);
    if n == 0 {
        return "^$";
    }
    let mut res = "^";
    let mut i = 0;
    while i < n {
        res = res + "#" + slice(s, i, i + 1);
        i = i + 1;
    }
    res = res + "#$";
    return res;
}

fn longest_palindromic_substring(s: str) -> str {
    let n = len(s);
    if n <= 1 {
        return s;
    }

    let t = manacher_preprocess(s);
    let m = len(t);

    let mut p = [];
    let mut idx = 0;
    while idx < m {
        p = p + [0];
        idx = idx + 1;
    }

    let mut center = 0;
    let mut right = 0;

    let mut i = 1;
    while i < (m - 1) {
        let i_mirror = 2 * center - i;
        if right > i {
            let mirror_rad = p[i_mirror];
            let bound_rad = right - i;
            if mirror_rad < bound_rad {
                p[i] = mirror_rad;
            } else {
                p[i] = bound_rad;
            }
        } else {
            p[i] = 0;
        }

        while slice(t, i + 1 + p[i], i + 1 + p[i] + 1) == slice(t, i - 1 - p[i], i - 1 - p[i] + 1) {
            p[i] = p[i] + 1;
        }

        if (i + p[i]) > right {
            center = i;
            right = i + p[i];
        }

        i = i + 1;
    }

    let mut max_len = 0;
    let mut center_idx = 0;
    let mut k = 1;
    while k < (m - 1) {
        if p[k] > max_len {
            max_len = p[k];
            center_idx = k;
        }
        k = k + 1;
    }

    let start = (center_idx - max_len) >> 1;
    return slice(s, start, start + max_len);
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_manacher_tutorial.ltl` validates:

1. **Classical Odd-Length Palindromes**:
   - `"racecar"` $\to$ `"racecar"`.
2. **Odd Palindrome Substring Inside Noise**:
   - `"abacdfgdcaba"` $\to$ `"aba"`.
3. **Classical Even-Length Palindromes**:
   - `"forgeeksskeegfor"` $\to$ `"geeksskeeg"`.
4. **Even Palindrome Substrings**:
   - `"cbbd"` $\to$ `"bb"`.
5. **Homogeneous Repeats**:
   - `"aaaaa"` $\to$ `"aaaaa"`.
6. **No Multi-Character Palindrome**:
   - `"abcdef"` $\to$ single character length 1.
7. **Single-Character and Empty String Base Cases**:
   - `"x"` $\to$ `"x"`, `""` $\to$ `""`.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_manacher_tutorial.ltl
python -m lateralus_lang check examples/manacher_tutorial.ltl
pytest tests/test_compiler.py
```
