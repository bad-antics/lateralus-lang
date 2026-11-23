# Mastering Levenshtein Distance in Lateralus: Dynamic Programming, Fuzzy Matching, and "Did you mean?" Diagnostics

User interfaces and developer tools frequently encounter mistyped identifiers, misspelled command-line flags, and approximate text queries. In modern compilers and toolchains (such as Rust, Git, and Clang), displaying helpful suggestions like:

```text
error: unknown command 'chek'
  did you mean 'check'?
```
dramatically improves developer experience and ergonomics.

The **Levenshtein Distance** is the foundational metric for measuring the minimum number of single-character edits (insertions, deletions, or substitutions) required to transform one string into another.

In this tutorial, we demonstrate how to implement, optimize, and test Levenshtein distance calculations natively in Lateralus.

---

## 1. Dynamic Programming Formulation (Wagner–Fischer Algorithm)

Given two strings $S_1$ of length $M$ and $S_2$ of length $N$, the edit distance matrix cell $D[i, j]$ represents the distance between prefixes $S_1[0 \dots i-1]$ and $S_2[0 \dots j-1]$:

$$D[i, j] = \begin{cases}
\max(i, j) & \text{if } \min(i, j) = 0 \\
\min \begin{cases}
D[i-1, j] + 1 & \text{(Deletion)} \\
D[i, j-1] + 1 & \text{(Insertion)} \\
D[i-1, j-1] + \text{cost} & \text{(Substitution)}
\end{cases} & \text{otherwise}
\end{cases}$$

where $\text{cost} = 0$ if $S_1[i-1] == S_2[j-1]$, else $1$.

---

## 2. Space Optimization: Two-Row Rolling Buffers

A naive matrix requires $O(M \times N)$ memory. Because computing row $i$ only requires data from row $i-1$, we reduce space complexity to $O(N)$ by keeping two alternating rows: `prev` and `curr`.

```lateralus
let mut i = 0;
while i < len1 {
    let ch1 = slice(s1, i, i + 1);
    let mut curr = [i + 1];
    let mut k = 0;
    while k < len2 {
        let ch2 = slice(s2, k, k + 1);
        let mut cost = 1;
        if ch1 == ch2 {
            cost = 0;
        }
        let deletion = prev[k + 1] + 1;
        let insertion = curr[k] + 1;
        let substitution = prev[k] + cost;
        curr.append(min3(deletion, insertion, substitution));
        k = k + 1;
    }
    prev = curr;
    i = i + 1;
}
```

---

## 3. Real-World Compiler Suggestion Engine ("Did you mean?")

When a user triggers an unrecognized identifier or flag, we iterate over known symbols and calculate edit distances. The candidate with the smallest distance below an acceptance threshold (typically $d \le 2$) is surfaced.

See `examples/levenshtein_tutorial.ltl` for a runnable demonstration resolving `chek` to `check`.

---

## 4. End-to-End Verification with Golden Test Vectors

We verify our implementation against standard benchmark test vectors:
- **Identical strings**: `levenshtein("apple", "apple") == 0`
- **Prefix / suffix deletions**: `levenshtein("", "test") == 4`
- **Classic Wagner-Fischer benchmarks**:
  - `kitten` $\to$ `sitting` = 3 (substitute `k` $\to$ `s`, substitute `e` $\to$ `i`, append `g`)
  - `flaw` $\to$ `lawn` = 2 (delete `f`, insert `n`)
  - `sunday` $\to$ `saturday` = 3

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/levenshtein_tutorial.ltl
python -m lateralus_lang check tests/stdlib_levenshtein_tutorial.ltl
pytest tests/test_compiler.py
```
