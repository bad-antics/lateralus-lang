# Mastering Binary Search in Lateralus: O(log N) Partition Points, Lower/Upper Bounds, and Overflow-Safe Invariants

In *Programming Pearls*, Jon Bentley famously observed that although the underlying concept of binary search is straightforward—halving the search space at each iteration—over 90% of software engineers introduce subtle boundary or off-by-one bugs when writing it from memory. Even the standard Java `java.util.Arrays.binarySearch` harbored a critical arithmetic overflow bug that remained undetected for nearly a decade.

Binary search is fundamentally a **monotone predicate partition algorithm**. It executes in strict $O(\log N)$ logarithmic time, reducing an inspection space of 1,000,000 items down to just 20 comparisons.

In this tutorial, we implement, benchmark, and mathematically verify an overflow-safe binary search engine in Lateralus, including `lower_bound`, `upper_bound`, and $O(\log N)$ frequency counting.

---

## 1. Mathematical Foundation: Monotone Predicates & Partition Points

Consider a sorted array $A = \langle a_0, a_1, \dots, a_{N-1} \rangle$ and a boolean predicate $P(x)$ that is monotonically increasing over indices:

$$P(i) \implies P(j) \quad \forall j \ge i$$

The array is cleanly partitioned into two contiguous regions:
$$\underbrace{\text{False, False, \dots, False}}_{i < k} \quad \Big| \quad \underbrace{\text{True, True, \dots, True}}_{i \ge k}$$

Binary search identifies the exact boundary index $k$ in $\lceil \log_2(N + 1) \rceil$ steps.

### 1.1 `lower_bound` vs. `upper_bound`

- **`lower_bound(A, target)`**: Uses predicate $P(i) \equiv (A[i] \ge \text{target})$. It returns the first index where elements are at least `target`.
- **`upper_bound(A, target)`**: Uses predicate $P(i) \equiv (A[i] > \text{target})$. It returns the first index where elements are strictly greater than `target`.

### 1.2 The $O(\log N)$ Duplicate Counting Invariant

For any value $x$ in a sorted array, the half-open interval $[\text{lower\_bound}(x), \text{upper\_bound}(x))$ contains every duplicate instance of $x$. Hence:

$$\operatorname{count}(A, x) = \operatorname{upper\_bound}(A, x) - \operatorname{lower\_bound}(A, x)$$

This computes exact frequency in $2 \log_2 N$ steps, completely avoiding $O(N)$ linear scans.

---

## 2. Invariant: Midpoint Overflow Prevention

The naive calculation:

$$\text{mid} = \frac{\text{low} + \text{high}}{2}$$

causes integer overflow when $\text{low} + \text{high} \ge 2^{31}$. In Lateralus, we enforce the overflow-immune formula:

$$\text{mid} = \text{low} + \left\lfloor \frac{\text{high} - \text{low}}{2} \right\rfloor$$

---

## 3. The Lateralus Implementation

### 3.1 Exact Match Binary Search

```lateralus
fn binary_search(arr: list, target: int) -> int {
    let mut low = 0;
    let mut high = len(arr) - 1;
    while low <= high {
        let mid = low + (high - low) / 2;
        if arr[mid] == target {
            return mid;
        } else if arr[mid] < target {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return -1;
}
```

### 3.2 Lower Bound ($A[i] \ge \text{target}$)

```lateralus
fn lower_bound(arr: list, target: int) -> int {
    let mut low = 0;
    let mut high = len(arr);
    while low < high {
        let mid = low + (high - low) / 2;
        if arr[mid] < target {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    return low;
}
```

### 3.3 Upper Bound ($A[i] > \text{target}$)

```lateralus
fn upper_bound(arr: list, target: int) -> int {
    let mut low = 0;
    let mut high = len(arr);
    while low < high {
        let mid = low + (high - low) / 2;
        if arr[mid] <= target {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    return low;
}
```

---

## 4. Verification and Execution

Run compiler checks and the test suite:

```powershell
# 1. Run interactive tutorial demo
lateralus_lang run examples/bsearch_tutorial.ltl

# 2. Run compiler check and unit test suite
lateralus_lang check tests/stdlib_bsearch_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus Logarithmic Binary Range Search Demo ===
Sorted Ledger Timestamps: [1000, 1050, 1100, 1100, 1100, 1200, 1350, 1500]
Exact Search for 1050 -> Found at index 1
Range Query for timestamp 1100:
  -> Lower Bound (first index >= 1100): 2
  -> Upper Bound (first index > 1100): 5
  -> Total Events in Batch: 3 (Evaluated in O(log N) time)
Optimal sorted insertion index for timestamp 1150: 5

Binary search and bound partitions verified 100% faithful!
```

---

## 5. Summary

Binary search illustrates how rigorous loop invariants eliminate off-by-one errors and guarantee logarithmic efficiency. In Lateralus, clean integer division and array indexing primitives enable constructing reliable range queries and lookup systems.
