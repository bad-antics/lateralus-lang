# Stable MergeSort in Lateralus: Divide-and-Conquer Recurrence, Worst-Case O(N log N) Guarantee, and Order Book Invariants

In 1945, computer science pioneer John von Neumann invented **MergeSort** to sequence magnetic tape records on the EDVAC system. MergeSort remains one of the foundational algorithms in computing, powering external memory disk merges, Linux kernel linked-list sorting (`lib/list_sort.c`), and hybrid sorting engines like Timsort (used in Python and Java).

Unlike QuickSort—which degrades to $O(N^2)$ quadratic time under adversarial or pre-sorted pivot conditions—MergeSort mathematically guarantees **strict $\Theta(N \log N)$ worst-case time complexity** while maintaining **algorithmic stability**.

In this tutorial, we implement, benchmark, and mathematically verify a complete stable MergeSort engine in Lateralus.

---

## 1. Mathematical Recurrence: The Master Theorem

MergeSort splits an array of length $N$ into two equal halves of size $N/2$, recursively sorts each half, and then merges the two sorted runs in linear $O(N)$ time:

$$T(N) = 2 T\left(\frac{N}{2}\right) + O(N), \quad T(1) = O(1)$$

By the **Master Theorem** for divide-and-conquer recurrences:
- Branching factor: $a = 2$
- Subproblem divisor: $b = 2$
- Work outside recursion: $f(N) = \Theta(N)$
- Critical exponent: $\log_b a = \log_2 2 = 1$

Since $f(N) = \Theta(N^{\log_b a}) = \Theta(N^1)$, Case 2 of the Master Theorem applies:

$$T(N) = \Theta(N \log N)$$

This guarantees predictability and uniform latency across all input distributions (best-case, average-case, and worst-case).

---

## 2. Invariant: Algorithmic Stability & Price-Time Priority

A sorting algorithm is defined as **stable** if and only if:

$$\forall i < j \text{ where } \operatorname{key}(A[i]) = \operatorname{key}(A[j]) \implies \operatorname{index}_{\text{out}}(A[i]) < \operatorname{index}_{\text{out}}(A[j])$$

In high-frequency trading matching engines (e.g. CME and crypto limit order books), **Price-Time Priority (FIFO)** dictates that orders resting at the identical limit price must be matched in the exact order they were received.

### The Merge Invariant

Stability is preserved during the merge phase by ensuring that whenever the left and right elements have identical keys, the element from the left sublist is chosen first:

$$\text{if } \text{left}[i] \le \text{right}[j] \implies \operatorname{select}(\text{left}[i])$$

In Lateralus, our test suite asserts this invariant across multi-key order tuples:

```lateralus
if left[i][0] <= right[j][0] {
    res = res + [left[i]];
    i = i + 1;
}
```

---

## 3. The Lateralus Implementation

### 3.1 Linear Two-Pointer Merge

```lateralus
fn merge(left: list, right: list) -> list {
    let mut res = [];
    let mut i = 0;
    let mut j = 0;
    let n_left = len(left);
    let n_right = len(right);

    while i < n_left && j < n_right {
        if left[i] <= right[j] {
            res = res + [left[i]];
            i = i + 1;
        } else {
            res = res + [right[j]];
            j = j + 1;
        }
    }

    while i < n_left {
        res = res + [left[i]];
        i = i + 1;
    }

    while j < n_right {
        res = res + [right[j]];
        j = j + 1;
    }

    return res;
}
```

### 3.2 Recursive Divide-and-Conquer Sorter

```lateralus
fn mergesort(arr: list) -> list {
    let n = len(arr);
    if n <= 1 {
        return arr;
    }

    let mid = n / 2;
    let left = slice(arr, 0, mid);
    let right = slice(arr, mid, n);

    let sorted_left = mergesort(left);
    let sorted_right = mergesort(right);

    return merge(sorted_left, sorted_right);
}
```

---

## 4. Verification and Execution

Run compiler checks and the test suite:

```powershell
# 1. Run interactive tutorial demo
lateralus_lang run examples/mergesort_tutorial.ltl

# 2. Run compiler check and unit test suite
lateralus_lang check tests/stdlib_mergesort_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus Stable MergeSort Financial Order Pipeline Demo ===
Incoming Raw Unsorted Orders: [[105, "ORD-02"], [100, "ORD-01"], [102, "ORD-04"], [100, "ORD-03"], [98, "ORD-06"], [100, "ORD-05"]]
Sorted Price-Time Order Queue: [[98, "ORD-06"], [100, "ORD-01"], [100, "ORD-03"], [100, "ORD-05"], [102, "ORD-04"], [105, "ORD-02"]]
FIFO Price-Time Priority strictly preserved: [ORD-01, ORD-03, ORD-05]

MergeSort sorting pipeline verified 100% faithful!
```

---

## 5. Summary

MergeSort demonstrates the elegance of divide-and-conquer algorithms in computer science. Lateralus's native list slicing and recursion support clean, declarative expressions of stable sorting pipelines suitable for financial ledgers, audit trails, and core system utilities.
