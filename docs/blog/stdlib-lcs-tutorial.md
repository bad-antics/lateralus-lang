# Longest Common Subsequence Tutorial: 2D Dynamic Programming and Sequence Reconstruction

## Overview

The **Longest Common Subsequence** (LCS) is an optimization problem in computer science that finds the longest sequence of characters that appears in the same relative order in two given strings $A$ and $B$, but not necessarily contiguously.

LCS is the theoretical foundation for:
- **Version Control Systems (VCS)**: Powering `diff` algorithms (such as the Myers diff algorithm and GNU `diff`), determining line insertion, deletion, and modification histories.
- **Data Deduplication**: Identifying shared redundant chunks across binary streams.
- **Computational Biology**: Aligning genomic DNA nucleotide sequences and protein chains to measure phylogenetic homology.

---

## 2D Dynamic Programming Recurrence

Let $A$ have length $m$ and $B$ have length $n$. We define $DP[i][j]$ as the length of the LCS of prefixes $A[0..i-1]$ and $B[0..j-1]$.

### Recurrence Relation

1. **Character Match ($A[i-1] == B[j-1]$)**:
   The matching character extends the LCS of the smaller prefixes:
   $$DP[i][j] = DP[i-1][j-1] + 1$$
2. **Character Mismatch ($A[i-1] \neq B[j-1]$)**:
   The optimal subsequence must come from either dropping the last character of $A$ or dropping the last character of $B$:
   $$DP[i][j] = \max(DP[i-1][j], DP[i][j-1])$$

Base cases:
$$DP[0][j] = 0 \quad \forall j \in [0, n]$$
$$DP[i][0] = 0 \quad \forall i \in [0, m]$$

### Backwards Traceback Reconstruction

After constructing the full $(m+1) \times (n+1)$ matrix:
- Start at index $(tr = m, tc = n)$.
- If $A[tr-1] == B[tc-1]$, this character was part of the LCS. Prepend $A[tr-1]$ to the result and step diagonally to $(tr-1, tc-1)$.
- Otherwise, step in the direction of the larger neighbor:
  - If $DP[tr-1][tc] > DP[tr][tc-1]$, step up: $tr \leftarrow tr - 1$.
  - Else, step left: $tc \leftarrow tc - 1$.
- Terminate when $tr == 0$ or $tc == 0$.

Time complexity is $O(m \cdot n)$ and auxiliary space is $O(m \cdot n)$.

---

## Lateralus Implementation

```lateralus
fn lcs(s1: str, s2: str) -> dict {
    let m = len(s1);
    let n = len(s2);

    let mut dp = [];
    let mut i = 0;
    while i <= m {
        let mut row = [];
        let mut j = 0;
        while j <= n {
            row = row + [0];
            j = j + 1;
        }
        dp = dp + [row];
        i = i + 1;
    }

    let mut r = 1;
    while r <= m {
        let c1 = slice(s1, r - 1, r);
        let mut c = 1;
        while c <= n {
            let c2 = slice(s2, c - 1, c);
            if c1 == c2 {
                dp[r][c] = dp[r - 1][c - 1] + 1;
            } else {
                let up = dp[r - 1][c];
                let left = dp[r][c - 1];
                if up > left {
                    dp[r][c] = up;
                } else {
                    dp[r][c] = left;
                }
            }
            c = c + 1;
        }
        r = r + 1;
    }

    let lcs_length = dp[m][n];

    let mut lcs_seq = "";
    let mut tr = m;
    let mut tc = n;
    while tr > 0 && tc > 0 {
        let c1 = slice(s1, tr - 1, tr);
        let c2 = slice(s2, tc - 1, tc);
        if c1 == c2 {
            lcs_seq = c1 + lcs_seq;
            tr = tr - 1;
            tc = tc - 1;
        } else {
            if dp[tr - 1][tc] > dp[tr][tc - 1] {
                tr = tr - 1;
            } else {
                tc = tc - 1;
            }
        }
    }

    let mut result = {};
    result["length"] = lcs_length;
    result["subsequence"] = lcs_seq;
    return result;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_lcs_tutorial.ltl` validates:

1. **Textbook Sequence**:
   - `"AGGTAB"` and `"GXTXAYB"` yields `"GTAB"`, length 4.
2. **Subsequence Matching**:
   - `"ABCDE"` and `"ACE"` yields `"ACE"`, length 3.
3. **Identical Sequences**:
   - Full identity `"LATERALUS"` yields full string.
4. **Completely Disjoint Sets**:
   - `"ABC"` and `"XYZ"` yields length 0.
5. **Boundary Cases**:
   - Empty string paired with non-empty string; two empty strings; single character matches and mismatches.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_lcs_tutorial.ltl
python -m lateralus_lang check examples/lcs_tutorial.ltl
pytest tests/test_compiler.py
```
