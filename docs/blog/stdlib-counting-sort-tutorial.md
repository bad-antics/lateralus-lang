---
title: "Linear-Time Non-Comparison Integer Sorting: Implementing Counting Sort in Lateralus"
description: "A comprehensive guide to Harold H. Seward's Counting Sort algorithm in Lateralus, breaking comparison sorting limits with O(n + k) performance and strict stability."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "sorting", "integers", "linear-time", "standard-library"]
---

# Linear-Time Non-Comparison Integer Sorting: Implementing Counting Sort in Lateralus

In algorithm design, standard comparison-based sorting algorithms (such as Quicksort, Mergesort, and Heapsort) are mathematically proven by decision tree models to have a lower bound of $\Omega(n \log n)$. 

However, when sorting keys are integers (or objects mappable to discrete bounded integer keys), we can break past the comparison barrier using **Counting Sort**, invented by **Harold H. Seward in 1954**. Counting Sort achieves strictly **linear $O(n + k)$** execution time where $n$ is the number of elements and $k$ is the span of input keys ($k = \max - \min + 1$).

Furthermore, when implemented with backward iteration during output distribution, Counting Sort is **strictly stable**, meaning equal keys preserve their initial relative order—a critical invariant when using it as a subroutine in Radix Sort.

---

## 1. Algorithm Mechanics and Invariants

Counting Sort operates in three distinct phases:

```
[Input: 4, 2, 2, 8, 3, 3, 1]
               │
               ▼ Phase 1: Frequency Histogram
Count Array: [0:0, 1:1, 2:2, 3:2, 4:1, 5:0, 6:0, 7:0, 8:1]
               │
               ▼ Phase 2: Prefix Cumulative Sums
Cumulative:  [1:1, 2:3, 3:5, 4:6, 5:6, 6:6, 7:6, 8:7]
(Each entry C[v] indicates the number of elements <= v)
               │
               ▼ Phase 3: Backward Distribution
Output Array: [1, 2, 2, 3, 3, 4, 8]
```

### 1.1 Phase 1: Frequency Histogram
We scan the input collection and tally the occurrence of each distinct key $v \in [\min, \max]$. To handle negative numbers seamlessly, every key is offset by subtracting $\min$:

$$\text{offset} = v - \min$$

### 1.2 Phase 2: Prefix Cumulative Sum
We transform the frequency array into a cumulative distribution:

$$\text{Count}[c] = \text{Count}[c] + \text{Count}[c - 1]$$

At this point, $\text{Count}[v - \min]$ represents the exact count of items less than or equal to $v$. Therefore, the last occurrence of $v$ belongs at index $\text{Count}[v - \min] - 1$.

### 1.3 Phase 3: Backward Distribution (Stability Invariant)
By iterating from $i = n - 1$ down to $0$, we place each element into its designated slot and decrement $\text{Count}[v - \min]$. Scanning backwards ensures that the element appearing later in the input is placed at the higher valid slot, preserving relative positioning and guaranteeing **$O(1)$ stability**.

---

## 2. Implementation in Lateralus

Below is the robust implementation of Counting Sort supporting arbitrary integer ranges:

```lateralus
pub fn counting_sort(arr, n) {
    if n <= 1 {
        return arr
    }

    // 1. Identify minimum and maximum bounds
    let min_val = arr[0]
    let max_val = arr[0]
    let i = 1
    while i < n {
        if arr[i] < min_val {
            min_val = arr[i]
        }
        if arr[i] > max_val {
            max_val = arr[i]
        }
        i = i + 1
    }

    let range_len = max_val - min_val + 1

    // 2. Initialize frequency table
    let count = dict()
    let c = 0
    while c < range_len {
        count[c] = 0
        c = c + 1
    }

    // 3. Populate frequency counts
    i = 0
    while i < n {
        let offset = arr[i] - min_val
        count[offset] = count[offset] + 1
        i = i + 1
    }

    // 4. Compute prefix cumulative counts
    c = 1
    while c < range_len {
        count[c] = count[c] + count[c - 1]
        c = c + 1
    }

    // 5. Stable backward distribution
    let output = dict()
    i = n - 1
    while i >= 0 {
        let val = arr[i]
        let offset = val - min_val
        let target_idx = count[offset] - 1
        output[target_idx] = val
        count[offset] = count[offset] - 1
        i = i - 1
    }

    return output
}
```

---

## 3. Complexity Analysis

| Metric | Complexity | Description |
| :--- | :--- | :--- |
| **Best-Case Time** | $O(n + k)$ | Three linear traversals over $n$ items and $k$ bins |
| **Average-Case Time**| $O(n + k)$ | Deterministic, non-comparison based |
| **Worst-Case Time** | $O(n + k)$ | No degenerate input permutations |
| **Auxiliary Space** | $O(n + k)$ | Space for output buffer ($n$) and counts ($k$) |
| **Stability** | **Yes** | Preserved via backward iteration |

When $k = O(n)$ (e.g., sorting ages, exam scores, ratings, or small bounded IDs), Counting Sort runs in asymptotically optimal linear time, vastly outperforming $O(n \log n)$ algorithms.

---

## 4. Verification and Practical Usage

The implementation is verified in `tests/stdlib_counting_sort_tutorial.ltl` covering:
- Bounded positive integers with duplicates
- Negative and zero values spanning $[-10, 8]$
- Pre-sorted and reverse-sorted collections
- Uniform arrays where all values are identical

An end-to-end e-commerce review rating distribution example is available in `examples/counting_sort_tutorial.ltl`.
