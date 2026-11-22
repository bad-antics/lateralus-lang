---
title: "Linear String Indexing: Implementing Suffix Automata (SAM) in Lateralus"
description: "A comprehensive guide to constructing Suffix Automata in Lateralus, compressing all O(n^2) substrings into O(n) states for instant O(m) pattern queries and linear distinct substring enumeration."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "data-structures", "strings", "automata", "standard-library"]
---

# Linear String Indexing: Implementing Suffix Automata (SAM) in Lateralus

In computational genomics (k-mer frequency counting and genetic primer matching), high-throughput network firewalls (Deep Packet Inspection for signature detection), and compression engines (LZ77/LZMA dictionary deduplication), indexing all substrings of a target string is a core computational primitive.

A string of length $n$ contains $\frac{n(n+1)}{2} = O(n^2)$ distinct substring occurrences. Building a naive trie requires quadratic $O(n^2)$ space, while Suffix Trees require complex Ukkonen-style edge splitting and large constant factors.

The **Suffix Automaton (SAM)**—introduced by **Blumer et al. (1983)** and refined by **Maxime Crochemore (1986)**—is the most compact deterministic acyclic finite automaton (DAFA) representing all substrings of a string:
- **Maximum States**: At most $2n - 1$ states (for $n > 1$).
- **Maximum Transitions**: At most $3n - 4$ transitions.
- **Construction Complexity**: Strictly linear $O(n)$ time and memory.
- **Pattern Matching Query**: Strictly $O(m)$ time matching the query length, independent of text size $n$.

---

## 1. Mathematical Foundations & Endpos Equivalence Classes

### 1.1 The Endpos Invariant

For any substring $s$ of text $T$, let $\text{endpos}(s)$ denote the set of all right-end positions where $s$ terminates in $T$:

$$\text{endpos}(s) = \{ r \mid T[r - |s| + 1 \dots r] = s \}$$

Two substrings $u$ and $v$ belong to the same **endpos-equivalence class** if and only if:
$$\text{endpos}(u) = \text{endpos}(v)$$

Each state in a Suffix Automaton corresponds to exactly one endpos-equivalence class.

### 1.2 Continuous Length Range & Suffix Links

> **Lemma**: For any state $u$, all substrings in its equivalence class have continuous lengths spanning:
> $$(\text{len}[\text{link}[u]], \text{len}[u]]$$

Where:
- $\text{len}[u]$ is the length of the longest substring accepted by state $u$.
- $\text{link}[u]$ points to the state corresponding to the longest suffix of substrings in $u$ that has a strictly larger endpos set (a parent in the suffix tree of the reversed text).

### 1.3 Total Distinct Substrings Formula

Because each state $u$ uniquely partitions distinct substrings by length:

$$\text{Distinct Substrings} = \sum_{u = 1}^{|\text{states}| - 1} (\text{len}[u] - \text{len}[\text{link}[u]])$$

---

## 2. Online Construction Mechanics (`sam_extend`)

As each character $c$ is appended to the text, a new state `cur` is allocated:

1. Follow suffix links backward from state `last` along parent pointers $p \leftarrow \text{link}[p]$, adding transitions $\text{next}[p][c] = \text{cur}$ until finding an ancestor with an existing transition on $c$.
2. If no ancestor has a transition on $c$ ($p = -1$), set $\text{link}[\text{cur}] = 0$ (the root state).
3. If an ancestor $p$ already has transition $q = \text{next}[p][c]$:
   - **Case A (Continuous Extension)**: If $\text{len}[p] + 1 = \text{len}[q]$, then $\text{link}[\text{cur}] = q$.
   - **Case B (State Splitting / Cloning)**: If $\text{len}[q] > \text{len}[p] + 1$, state $q$ contains longer substrings that do not extend $p$. We duplicate state $q$ into a new `clone` state with $\text{len}[\text{clone}] = \text{len}[p] + 1$, copy $q$'s transitions, redirect ancestral edges pointing to $q$ to `clone`, and update suffix links:
     $$\text{link}[q] = \text{clone}, \quad \text{link}[\text{cur}] = \text{clone}$$

---

## 3. Lateralus Implementation

Here is the clean implementation of `stdlib/suffix_automaton.ltl`:

```lateralus
pub fn new_sam() {
    let sam = dict()
    sam["states"] = dict()
    sam["sz"] = 1
    sam["last"] = 0
    
    let init_state = dict()
    init_state["len"] = 0
    init_state["link"] = -1
    init_state["next"] = dict()
    sam["states"][0] = init_state
    return sam
}

pub fn sam_extend(sam, ch) {
    let cur = sam["sz"]
    sam["sz"] = cur + 1

    let cur_state = dict()
    cur_state["len"] = sam["states"][sam["last"]]["len"] + 1
    cur_state["link"] = -1
    cur_state["next"] = dict()
    sam["states"][cur] = cur_state

    let p = sam["last"]
    while p != -1 {
        let p_state = sam["states"][p]
        if p_state["next"][ch] != nil {
            break
        }
        p_state["next"][ch] = cur
        p = p_state["link"]
    }

    if p == -1 {
        cur_state["link"] = 0
    } else {
        let p_state = sam["states"][p]
        let q = p_state["next"][ch]
        let q_state = sam["states"][q]
        if p_state["len"] + 1 == q_state["len"] {
            cur_state["link"] = q
        } else {
            let clone = sam["sz"]
            sam["sz"] = clone + 1

            let clone_state = dict()
            clone_state["len"] = p_state["len"] + 1
            clone_state["link"] = q_state["link"]
            let copy_next = dict()
            for key in q_state["next"] {
                copy_next[key] = q_state["next"][key]
            }
            clone_state["next"] = copy_next
            sam["states"][clone] = clone_state

            while p != -1 {
                let curr_p = sam["states"][p]
                if curr_p["next"][ch] != q {
                    break
                }
                curr_p["next"][ch] = clone
                p = curr_p["link"]
            }

            q_state["link"] = clone
            cur_state["link"] = clone
        }
    }

    sam["last"] = cur
    return cur
}

pub fn sam_count_distinct_substrings(sam) {
    let total = 0
    let sz = sam["sz"]
    let u = 1
    while u < sz {
        let u_state = sam["states"][u]
        let link_id = u_state["link"]
        let link_len = 0
        if link_id != -1 {
            link_len = sam["states"][link_id]["len"]
        }
        let diff = u_state["len"] - link_len
        total = total + diff
        u = u + 1
    }
    return total
}

pub fn sam_contains(sam, pattern_chars, pat_len) {
    let curr = 0
    let i = 0
    while i < pat_len {
        let ch = pattern_chars[i]
        let curr_state = sam["states"][curr]
        let next_node = curr_state["next"][ch]
        if next_node == nil {
            return false
        }
        curr = next_node
        i = i + 1
    }
    return true
}
```

---

## 4. Practical Application: Genomic DNA Motif Discovery & DPI Signature Filter

In biological sequence analysis, screening long DNA sequences for specific short primer segments or viral motifs must occur at wire speed:

```lateralus
pub fn run_genomic_dna_pipeline() {
    let sam = new_sam()

    // Stream DNA sequence of target gene: "GATTACA"
    sam_extend(sam, "G")
    sam_extend(sam, "A")
    sam_extend(sam, "T")
    sam_extend(sam, "T")
    sam_extend(sam, "A")
    sam_extend(sam, "C")
    sam_extend(sam, "A")

    // Count all distinct genetic motifs in linear O(n)
    let distinct_motifs = sam_count_distinct_substrings(sam)

    // O(m) Primer Verification
    let primer1 = dict()
    primer1[0] = "A"
    primer1[1] = "T"
    primer1[2] = "T"
    primer1[3] = "A"
    let has_primer1 = sam_contains(sam, primer1, 4) // Returns true

    let primer2 = dict()
    primer2[0] = "T"
    primer2[1] = "A"
    primer2[2] = "C"
    primer2[3] = "A"
    let has_primer2 = sam_contains(sam, primer2, 4) // Returns true
}
```

---

## 5. Automated Verification & Invariants Testing

The verification test suite in `tests/stdlib_suffix_automaton_tutorial.ltl` validates:
1. **Empty Automaton Invariant**: Zero length text yields 0 distinct substrings and 1 initial state.
2. **Exact Distinct Count Invariance**: On string `"abaa"`, exactly 8 distinct substrings (`"a"`, `"b"`, `"ab"`, `"ba"`, `"aa"`, `"aba"`, `"baa"`, `"abaa"`) are produced, adhering to state bounds $\le 2n - 1$.
3. **Linear State Cloning**: On repeated character strings like `"aaaa"`, states clone cleanly without memory leakage, yielding 4 substrings.
4. **Pattern Matching Exactness**: Every valid substring evaluates to `true` in $O(m)$ transitions, while invalid substrings terminate at `nil`.

Execute the test suite with:

```bash
lateralus check tests/stdlib_suffix_automaton_tutorial.ltl
lateralus check examples/suffix_automaton_tutorial.ltl
pytest tests/test_compiler.py
```
