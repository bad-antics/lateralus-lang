---
title: "Linear Expected Time Distribution Sorting: Implementing Bucket Sort in Lateralus"
description: "A comprehensive guide to implementing Bucket Sort in Lateralus, partitioning continuous distributions into discrete buckets to achieve linear expected O(n) runtime."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "sorting", "distribution", "linear-time", "standard-library"]
---

# Linear Expected Time Distribution Sorting: Implementing Bucket Sort in Lateralus

While general comparison-based sorts require $\Omega(n \log n)$ time, distribution-based sorting algorithms leverage assumptions about input data probability density functions to sort in **linear expected time $O(n)$**.

**Bucket Sort** (popularized by Donald Knuth in *The Art of Computer Programming*) divides the interval between the minimum and maximum elements into $k$ equal-sized sub-intervals (buckets). When input elements are uniformly distributed over the interval, each bucket contains an expected $O(1)$ items. Sorting each bucket individually with a stable algorithm (like Insertion Sort) and concatenating the results yields a globally sorted array in **$O(n)$ expected time**.

---

## 1. Mathematical Mechanics & Uniform Distribution Expectation

Bucket Sort executes a canonical **Scatter-Sort-Gather** pipeline:

```
[Input: 78, 17, 39, 26, 72, 94, 21, 12, 23, 68] (Min: 12, Max: 94)
                               │
               ▼ Step 1: Scatter into 5 Buckets
Bucket 0 [12-28]: [17, 26, 21, 12, 23]
Bucket 1 [29-44]: [39]
Bucket 2 [45-60]: []
Bucket 3 [61-77]: [72, 68]
Bucket 4 [78-94]: [78, 94]
                               │
               ▼ Step 2: Sort Each Bucket (Insertion Sort)
Bucket 0: [12, 17, 21, 23, 26]
Bucket 1: [39]
Bucket 2: []
Bucket 3: [68, 72]
Bucket 4: [78, 94]
                               │
               ▼ Step 3: Gather & Concatenate
Output: [12, 17, 21, 23, 26, 39, 68, 72, 78, 94]
```

### 1.1 Expected Complexity Proof

Let $n$ be the number of items distributed among $k$ buckets. If elements are independent and uniformly distributed:
1. The number of elements $n_i$ falling into bucket $i$ follows a binomial distribution $B(n, 1/k)$.
2. The runtime of sorting bucket $i$ via insertion sort is $O(n_i^2)$.
3. Taking the mathematical expectation:
   $$\mathbb{E}[T(n)] = \sum_{i=0}^{k-1} \mathbb{E}[O(n_i^2)] = O(n) + O\left(\sum_{i=0}^{k-1} \left(\frac{n}{k} + \frac{n(n-1)}{k^2}\right)\right)$$
4. Setting $k \propto n$, we obtain:
   $$\mathbb{E}[T(n)] = O(n)$$

---

## 2. Implementation in Lateralus

Below is the production-grade implementation of Bucket Sort with dynamic range normalization in Lateralus:

```lateralus
pub fn insertion_sort(bucket, size) {
    let i = 1
    while i < size {
        let key = bucket[i]
        let j = i - 1
        while j >= 0 && bucket[j] > key {
            bucket[j + 1] = bucket[j]
            j = j - 1
        }
        bucket[j + 1] = key
        i = i + 1
    }
    return bucket
}

pub fn bucket_sort(arr, n, num_buckets) {
    if n <= 1 {
        return arr
    }

    // 1. Find min and max bounds
    let min_val = arr[0]
    let max_val = arr[0]
    let i = 1
    while i < n {
        if arr[i] < min_val { min_val = arr[i] }
        if arr[i] > max_val { max_val = arr[i] }
        i = i + 1
    }

    if min_val == max_val {
        return arr
    }

    let range_span = max_val - min_val

    // 2. Initialize bucket data structures
    let buckets = dict()
    let bucket_sizes = dict()
    let b = 0
    while b < num_buckets {
        buckets[b] = dict()
        bucket_sizes[b] = 0
        b = b + 1
    }

    // 3. Scatter phase
    i = 0
    while i < n {
        let val = arr[i]
        let b_idx = ((val - min_val) * (num_buckets - 1)) / range_span
        if b_idx >= num_buckets {
            b_idx = num_buckets - 1
        }
        let cur_sz = bucket_sizes[b_idx]
        buckets[b_idx][cur_sz] = val
        bucket_sizes[b_idx] = cur_sz + 1
        i = i + 1
    }

    // 4. Sort phase (local insertion sort)
    b = 0
    while b < num_buckets {
        let sz = bucket_sizes[b]
        if sz > 1 {
            buckets[b] = insertion_sort(buckets[b], sz)
        }
        b = b + 1
    }

    // 5. Gather phase
    let output = dict()
    let out_idx = 0
    b = 0
    while b < num_buckets {
        let sz = bucket_sizes[b]
        let j = 0
        while j < sz {
            output[out_idx] = buckets[b][j]
            out_idx = out_idx + 1
            j = j + 1
        }
        b = b + 1
    }

    return output
}
```

---

## 3. Complexity & Boundary Properties

| Metric | Complexity | Condition |
| :--- | :--- | :--- |
| **Best-Case Time** | $O(n + k)$ | Elements evenly dispersed into $k$ buckets |
| **Expected Time** | $O(n)$ | Input follows uniform probability distribution |
| **Worst-Case Time** | $O(n^2)$ | All elements cluster into a single bucket |
| **Auxiliary Space** | $O(n + k)$ | Buffer for bucket structures |
| **Stability** | **Yes** | Insertion sort preserves equal element order |

---

## 4. Verification and Practical Applications

The verification suite in `tests/stdlib_bucket_sort_tutorial.ltl` checks:
- Standard positive distributions spanning 10 elements across 5 buckets
- Negative values and zero crossing $[-40, 25]$
- Arrays with identical/uniform elements
- Single-element arrays

A real-world IoT weather telemetry station application is provided in `examples/bucket_sort_tutorial.ltl`.
