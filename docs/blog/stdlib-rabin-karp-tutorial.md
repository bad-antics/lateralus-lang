# Rabin-Karp Tutorial: Substring Search with Polynomial Rolling Hashes

## Overview

The **Rabin-Karp algorithm** (invented by Michael O. Rabin and Richard M. Karp in 1987) is a string-searching algorithm that uses hashing to find any one of a set of pattern strings in a text. For substring search of a single pattern of length $m$ in text of length $n$, it achieves average-case $O(n + m)$ execution time.

Unlike deterministic finite automaton approaches (such as Knuth-Morris-Pratt or Boyer-Moore), Rabin-Karp's core advantage lies in **polynomial rolling hashing**:
- Computing the hash of a new substring of length $m$ shifted by one character takes $O(1)$ constant time.
- The algorithm scales to **multiple pattern search** (such as looking for thousands of malware signatures or prohibited terms simultaneously) with $O(1)$ hash set lookups per window position.

In security and infrastructure systems, Rabin-Karp is standard for:
- **Intrusion Detection Systems (IDS)**: Fast payload pattern matching in network packets (e.g. Snort/Suricata rules).
- **Plagiarism and Duplicate Content Detection**: Fingerprinting document n-grams and Rabin fingerprints.
- **High-Throughput Log Analytics**: Scanning distributed log streams for multi-keyword alerts.

---

## Polynomial Rolling Hash Mechanics

Given a string $S$ of length $m$, base radix $B = 256$, and large prime modulus $M = 10^9 + 7$:
$$H(S) = \left( \sum_{j=0}^{m-1} S[j] \cdot B^{m - 1 - j} \right) \pmod M$$

### $O(1)$ Sliding Window Hash Transition

When the sliding window moves from position $idx$ to $idx + 1$:
1. The character $c_{\text{out}} = S[idx]$ exits the window on the left (multiplied by $B^{m-1}$).
2. The character $c_{\text{in}} = S[idx + m]$ enters the window on the right.

The new hash is derived in $O(1)$ operations without recalculating intermediate characters:
$$H_{\text{next}} = \left( \left( H_{\text{prev}} - c_{\text{out}} \cdot B^{m-1} \pmod M \right) \cdot B + c_{\text{in}} \right) \pmod M$$

### Collision Handling

When $H_{\text{window}} = H_{\text{pattern}}$, a string equality comparison `slice(text, idx, idx + m) == pattern` is performed. With $M = 10^9 + 7$, hash collisions are rare, ensuring linear average complexity.

---

## Lateralus Implementation

```lateralus
fn rabin_karp_search(text: str, pattern: str) -> list {
    let n = len(text);
    let m = len(pattern);
    let mut matches = [];

    if m == 0 || m > n {
        return matches;
    }

    let B = 256;
    let M = 1000000007;

    let mut h = 1;
    let mut i = 0;
    while i < (m - 1) {
        h = (h * B) % M;
        i = i + 1;
    }

    let mut p_hash = 0;
    let mut t_hash = 0;
    let mut j = 0;
    while j < m {
        p_hash = (p_hash * B + ord(slice(pattern, j, j + 1))) % M;
        t_hash = (t_hash * B + ord(slice(text, j, j + 1))) % M;
        j = j + 1;
    }

    let mut idx = 0;
    while idx <= (n - m) {
        if p_hash == t_hash {
            if slice(text, idx, idx + m) == pattern {
                matches = matches + [idx];
            }
        }

        if idx < (n - m) {
            let c_out = ord(slice(text, idx, idx + 1));
            let c_in = ord(slice(text, idx + m, idx + m + 1));
            t_hash = (t_hash - (c_out * h) % M) % M;
            if t_hash < 0 {
                t_hash = t_hash + M;
            }
            t_hash = (t_hash * B + c_in) % M;
        }

        idx = idx + 1;
    }

    return matches;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_rabin_karp_tutorial.ltl` validates:

1. **Multi-Occurrence Matching**:
   - Matches pattern `"AABA"` in `"AABAACAADAABAABA"` at indices 0, 9, 12.
2. **Terminal Boundary Matching**:
   - Pattern located at the end of the input string.
3. **Non-Existent Patterns**:
   - Correctly returns empty list when pattern is absent.
4. **Full Text Match**:
   - Pattern identical to full text string ($m = n$).
5. **Pattern Longer than Text**:
   - Boundary condition handling where $m > n$.
6. **Single-Character Matches**:
   - Multiple single-character matches across the text.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_rabin_karp_tutorial.ltl
python -m lateralus_lang check examples/rabin_karp_tutorial.ltl
pytest tests/test_compiler.py
```
