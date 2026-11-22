---
title: "Linear Palindrome Indexing: Implementing Palindromic Trees (PAM) in Lateralus"
description: "A comprehensive guide to constructing the Rubinchik-Shur Palindromic Tree (EERTREE / PAM) in Lateralus for linear O(n) palindrome indexing and RNA hairpin analysis."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "strings", "palindromes", "automata", "genomics", "standard-library"]
---

# Linear Palindrome Indexing: Implementing Palindromic Trees (PAM) in Lateralus

In bioinformatics (identifying CRISPR palindromic repeat sequences and predicting RNA secondary stem-loop structures), text compression, and natural language processing, detecting and indexing palindromic substrings is a foundational operation.

While Manacher's algorithm identifies the longest palindromic substring in $O(n)$ time, it does not maintain an indexable graph of all distinct palindromes. Building a general Suffix Automaton or Suffix Tree indices all substrings, incurring higher overhead.

The **Palindromic Tree (PAM)**—also known as the **EERTREE**, introduced by **Mikhail Rubinchik and Arseny M. Shur in 2013**—is a specialized automaton designed exclusively for palindromic substrings:
- **State Bound**: A string of length $n$ contains at most $n$ distinct non-empty palindromic substrings. The tree contains at most $n + 2$ total states.
- **Construction Time**: Strictly linear $O(n)$ amortized time.
- **Topology**: Directed acyclic graph with two imaginary roots representing even and odd symmetries.

---

## 1. Dual-Root Architecture & Suffix Links

Every palindrome possesses either an odd length (symmetric around a central character, e.g. `"aba"`) or an even length (symmetric around a central boundary, e.g. `"abba"`). To represent this cleanly without special-case branching, the Palindromic Tree utilizes two distinct root nodes:

### 1.1 The Two Imaginary Roots
1. **Odd Root (State 1, Length $-1$)**:
   The base for odd-length palindromes. Transitioning on character $c$ creates a palindrome of length $(-1) + 2 = 1$ (the single character $c$). Its suffix link points to itself.
2. **Even Root (State 0, Length $0$)**:
   The base for even-length palindromes. Transitioning on character $c$ creates a palindrome of length $0 + 2 = 2$ (the twin characters $cc$). Its suffix link points to the Odd Root (State 1).

### 1.2 Transition Invariant
An edge labeled with character $c$ from state $u$ (representing palindrome $P$) leads to state $v$ representing:
$$v = c + P + c, \quad \text{len}[v] = \text{len}[u] + 2$$

### 1.3 Suffix Link Invariant
For any state $u$, its suffix link $\text{link}[u]$ points to the state representing the **longest proper palindromic suffix** of the palindrome corresponding to $u$.

```
         (Odd Root, Len -1)  <--------------------+
           |             ^                        |
           | 'a'         | link                   | link
           v             |                        |
         ("a", Len 1)  (Even Root, Len 0)        |
           |             |                        |
           | 'b'         | 'b'                    |
           v             v                        |
        ("aba", Len 3) ("bb", Len 2) -------------+
```

---

## 2. Online Construction Mechanics (`pam_add`)

When appending character $S[n]$:

1. **Locate Extending Context**: Starting at state `last` (the longest palindromic suffix of $S[0 \dots n-1]$), follow suffix links $p \leftarrow \text{link}[p]$ until finding a state $p$ such that the character preceding $p$'s palindrome in $S$ matches $S[n]$:
   $$S[n - \text{len}[p] - 1] == S[n]$$
2. **Check Existing State**: If state $p$ already has an outgoing transition on $S[n]$, the palindrome $S[n] + p + S[n]$ has already been discovered. Set `last = next[p][S[n]]` and return.
3. **Create New State**: Otherwise, allocate a new state `cur` with $\text{len}[\text{cur}] = \text{len}[p] + 2$.
4. **Compute Suffix Link**:
   - If $\text{len}[\text{cur}] = 1$, $\text{link}[\text{cur}] = 0$ (Even root).
   - Otherwise, traverse suffix links starting from $\text{link}[p]$ to find the longest proper palindromic suffix matching before $S[n]$, setting $\text{link}[\text{cur}] = \text{next}[\text{matching\_node}][S[n]]$.
5. **Attach Edge**: Set $\text{next}[p][S[n]] = \text{cur}$ and update `last = cur`.

---

## 3. Lateralus Implementation

Here is the clean implementation of `stdlib/palindromic_tree.ltl`:

```lateralus
pub fn new_pam() {
    let pam = dict()
    pam["nodes"] = dict()
    pam["sz"] = 2
    pam["n"] = 0
    pam["last"] = 0
    pam["s"] = dict()

    let even_root = dict()
    even_root["len"] = 0
    even_root["link"] = 1
    even_root["next"] = dict()
    pam["nodes"][0] = even_root

    let odd_root = dict()
    odd_root["len"] = 0 - 1
    odd_root["link"] = 1
    odd_root["next"] = dict()
    pam["nodes"][1] = odd_root

    return pam
}

pub fn pam_get_link(pam, p) {
    let n = pam["n"]
    while true {
        let p_state = pam["nodes"][p]
        let p_len = p_state["len"]
        let target_idx = n - p_len - 1
        if target_idx >= 0 {
            if pam["s"][target_idx] == pam["s"][n] {
                return p
            }
        }
        if p == 1 {
            return 1
        }
        p = p_state["link"]
    }
    return 1
}

pub fn pam_add(pam, ch) {
    let n = pam["n"]
    pam["s"][n] = ch

    let p = pam_get_link(pam, pam["last"])
    let p_state = pam["nodes"][p]

    if p_state["next"][ch] != nil {
        pam["last"] = p_state["next"][ch]
        pam["n"] = n + 1
        return pam["last"]
    }

    let cur = pam["sz"]
    pam["sz"] = cur + 1

    let cur_state = dict()
    cur_state["len"] = p_state["len"] + 2
    cur_state["next"] = dict()

    if cur_state["len"] == 1 {
        cur_state["link"] = 0
    } else {
        let link_p = pam_get_link(pam, p_state["link"])
        cur_state["link"] = pam["nodes"][link_p]["next"][ch]
    }

    p_state["next"][ch] = cur
    pam["nodes"][cur] = cur_state
    pam["last"] = cur
    pam["n"] = n + 1
    return cur
}

pub fn pam_distinct_count(pam) {
    return pam["sz"] - 2
}

pub fn pam_longest_palindrome_len(pam) {
    let max_len = 0
    let sz = pam["sz"]
    let u = 2
    while u < sz {
        let l = pam["nodes"][u]["len"]
        if l > max_len {
            max_len = l
        }
        u = u + 1
    }
    return max_len
}
```

---

## 4. Practical Application: RNA Hairpin Loop & CRISPR Repeat Detection

In RNA folding, inverted palindromic sequences fold back on themselves to create stable hairpin stem-loops. PAM calculates both the maximum stem length and unique binding motifs in real time:

```lateralus
pub fn run_crispr_rna_pipeline() {
    let pam = new_pam()

    // Stream RNA segment: "AUGCGU" -> "AUGCGU A"
    pam_add(pam, "A")
    pam_add(pam, "U")
    pam_add(pam, "G")
    pam_add(pam, "C")
    pam_add(pam, "G")
    pam_add(pam, "U")
    pam_add(pam, "A")

    // Computes unique palindromic binding sites and peak loop length
    let unique_motifs = pam_distinct_count(pam)
    let max_hairpin_len = pam_longest_palindrome_len(pam)
}
```

---

## 5. Verification & Testing

The verification test suite in `tests/stdlib_palindromic_tree_tutorial.ltl` validates:
1. **Dual Root Initialization**: Even root (0) and Odd root (-1) establish baseline symmetries.
2. **Canonical Multi-Palindrome Invariant**: String `"abacaba"` yields exactly 6 distinct non-empty palindromic substrings (`"a"`, `"b"`, `"c"`, `"aba"`, `"bacab"`, `"abacaba"`), with maximum length 7.
3. **Homogeneous Text Bound**: On `"aaaa"`, asserts exactly 4 distinct palindromes (`"a"`, `"aa"`, `"aaa"`, `"aaaa"`).

Execute the test suite with:

```bash
lateralus check tests/stdlib_palindromic_tree_tutorial.ltl
lateralus check examples/palindromic_tree_tutorial.ltl
pytest tests/test_compiler.py
```
