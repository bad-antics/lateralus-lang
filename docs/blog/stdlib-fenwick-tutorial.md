# Fenwick Tree Tutorial: Binary Indexed Trees for $O(\log n)$ Prefix Sums

## Overview

A **Fenwick Tree** (also known as a **Binary Indexed Tree**, or **BIT**), proposed by Peter Fenwick in 1994, is a data structure providing efficient $O(\log n)$ point updates and prefix sum queries over numeric arrays, utilizing $O(n)$ space.

Compared to standard prefix-sum arrays (which offer $O(1)$ query but $O(n)$ update) and segment trees (which require $4n$ space and pointer/node overhead), the Fenwick Tree operates entirely in-place over an implicit binary tree encoded in array indices using bitwise two's complement arithmetic.

In financial trading engines and metrics telemetry, Fenwick Trees are used for:
- **Order-Book Cumulative Depth**: Calculating volume resting up to an arbitrary price level in $O(\log n)$ time as limit orders are inserted and canceled.
- **Dynamic Rank & Quantile Estimation**: Real-time frequency counting and quantile thresholding.
- **Inversion Counting**: Evaluating sorting metric entropy in permutation algorithms.

---

## Theoretical Foundation: The Lowbit Operation

The fundamental insight of a Fenwick Tree is that every positive integer $i$ can be uniquely expressed as a sum of powers of 2.

The lowest set bit (least significant bit with value 1) of an integer $i$ is isolated using two's complement bitwise AND:
$$\text{lowbit}(i) = i \ \& \ (-i) = i \ \& \ (0 - i)$$

In a 1-based array `tree[1..n]`:
- Each index $i$ stores the cumulative sum of the range:
  $$(i - \text{lowbit}(i), i]$$
  representing $\text{lowbit}(i)$ consecutive elements ending at index $i$.

### Point Update: $i \leftarrow i + \text{lowbit}(i)$

When a delta $\Delta$ is added to index $i$, all tree nodes whose intervals cover $i$ must be updated. This is achieved by traversing up the ancestor chain:
$$i \leftarrow i + \text{lowbit}(i)$$
terminating when $i > n$.

### Prefix Query: $i \leftarrow i - \text{lowbit}(i)$

To compute the prefix sum $\sum_{k=1}^i A[k]$, the algorithm accumulates `tree[i]` and strips the least significant bit:
$$i \leftarrow i - \text{lowbit}(i)$$
terminating when $i = 0$.

### Range Sum Query

The sum of elements in arbitrary interval $[L, R]$ is computed via prefix subtraction:
$$\text{sum}(L, R) = \text{query}(R) - \text{query}(L - 1)$$

---

## Lateralus Implementation

```lateralus
fn lowbit(x: int) -> int {
    return x & (0 - x);
}

fn fenwick_add(tree: list, size: int, idx: int, delta: int) -> list {
    let mut t = tree;
    let mut i = idx;
    while i <= size {
        t[i] = t[i] + delta;
        i = i + lowbit(i);
    }
    return t;
}

fn fenwick_query(tree: list, idx: int) -> int {
    let mut sum = 0;
    let mut i = idx;
    while i > 0 {
        sum = sum + tree[i];
        i = i - lowbit(i);
    }
    return sum;
}

fn fenwick_range_query(tree: list, left: int, right: int) -> int {
    if left > right {
        return 0;
    }
    return fenwick_query(tree, right) - fenwick_query(tree, left - 1);
}

fn fenwick_build(arr: list) -> list {
    let n = len(arr);
    let mut tree = [];
    let mut i = 0;
    while i <= n {
        tree = tree + [0];
        i = i + 1;
    }
    let mut idx = 1;
    while idx <= n {
        tree = fenwick_add(tree, n, idx, arr[idx - 1]);
        idx = idx + 1;
    }
    return tree;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_fenwick_tutorial.ltl` validates:

1. **Bitwise Lowbit Invariant**:
   - `lowbit(1)=1`, `lowbit(2)=2`, `lowbit(4)=4`, `lowbit(6)=2`, `lowbit(12)=4`.
2. **Classical Array Build & Prefix Invariants**:
   - Array `[3, 2, -1, 6, 5, 4, -3, 2]` verifying exact prefix sums $P(1)..P(8)$.
3. **Range Sum Queries**:
   - Arbitrary interval sums, e.g., $\text{sum}[2..5] = 12$, $\text{sum}[4..7] = 12$.
4. **Dynamic Point Updates**:
   - Updating index 3 with delta $+4$ and verifying propagation through $P(3), P(4), P(8)$.
5. **Single-Element Base Case**:
   - Boundary checks with single-element arrays.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_fenwick_tutorial.ltl
python -m lateralus_lang check examples/fenwick_tutorial.ltl
pytest tests/test_compiler.py
```
