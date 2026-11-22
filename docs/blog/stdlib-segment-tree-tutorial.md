# Segment Tree Tutorial: Range Minimum Queries and Point Updates

## Overview

A **Segment Tree** is a versatile binary tree data structure used for storing intervals or segments. It allows querying which of the stored segments contain a given point or computing range associative aggregations (such as range minimum/maximum queries (RMQ), range sum, or range GCD) in $O(\log n)$ time, while simultaneously supporting point or range updates in $O(\log n)$ time.

Unlike a Fenwick Tree (Binary Indexed Tree), which relies on invertible prefix operations (like addition/subtraction), a Segment Tree works seamlessly over **arbitrary semi-groups and monoids**, including idempotent operations:
- $\min(a, b)$
- $\max(a, b)$
- $\gcd(a, b)$
- Matrix multiplication

In infrastructure systems and high-throughput engines, Segment Trees power:
- **Server Telemetry and SLA Monitoring**: Computing rolling minimum/maximum latencies across arbitrary dynamic time intervals.
- **Financial Market Microstructure**: Answering Range Minimum/Maximum queries on discrete order-book queues and tick-by-tick spread analysis.
- **Computational Geometry**: Solving interval intersection, stabbing queries, and skyline algorithms.

---

## Architecture and Indexing

For an input array of length $n$, the Segment Tree is represented as a static 1-based array of size at most $4n$:
- **Root Node**: `node = 1`, representing the full range $[0, n-1]$.
- **Left Child**: `2 * node`, representing $[ \text{start}, \text{mid} ]$.
- **Right Child**: `2 * node + 1`, representing $[ \text{mid} + 1, \text{end} ]$.
- **Midpoint Division**: $\text{mid} = (\text{start} + \text{end}) \gg 1$.

```
                 [0..7] (node 1)
                /               \
         [0..3] (node 2)         [4..7] (node 3)
         /             \         /             \
    [0..1] (4)     [2..3] (5)  [4..5] (6)     [6..7] (7)
    /    \         /    \      /    \         /    \
   0      1       2      3    4      5       6      7
```

### Building in $O(n)$

Leaves represent individual array elements $arr[start]$. Each internal node computes the associative aggregation of its left and right children:
$$\text{tree}[\text{node}] = \min(\text{tree}[2 \cdot \text{node}], \text{tree}[2 \cdot \text{node} + 1])$$

### Range Query in $O(\log n)$

When querying interval $[L, R]$:
1. If the current segment $[ \text{start}, \text{end} ]$ is entirely outside $[L, R]$, return neutral element $\infty$ (`INF`).
2. If $[ \text{start}, \text{end} ]$ is completely contained within $[L, R]$, return $\text{tree}[\text{node}]$.
3. Otherwise, recursively query both children and return $\min(\text{left\_min}, \text{right\_min})$.

### Point Update in $O(\log n)$

When updating index $idx$ to value $val$:
- Traverse down to the target leaf corresponding to $idx$.
- Update leaf value.
- Recompute min aggregations on the return path back up to the root.

---

## Lateralus Implementation

```lateralus
fn seg_min(a: int, b: int) -> int {
    if a < b {
        return a;
    }
    return b;
}

fn seg_build(node: int, start: int, end: int, arr: list, tree: list) -> list {
    let mut t = tree;
    if start == end {
        t[node] = arr[start];
        return t;
    }
    let mid = (start + end) >> 1;
    t = seg_build(2 * node, start, mid, arr, t);
    t = seg_build(2 * node + 1, mid + 1, end, arr, t);
    t[node] = seg_min(t[2 * node], t[2 * node + 1]);
    return t;
}

fn seg_query(node: int, start: int, end: int, l: int, r: int, tree: list) -> int {
    let INF = 1000000000;
    if r < start || end < l {
        return INF;
    }
    if l <= start && end <= r {
        return tree[node];
    }
    let mid = (start + end) >> 1;
    let left_min = seg_query(2 * node, start, mid, l, r, tree);
    let right_min = seg_query(2 * node + 1, mid + 1, end, l, r, tree);
    return seg_min(left_min, right_min);
}

fn seg_update(node: int, start: int, end: int, idx: int, val: int, tree: list) -> list {
    let mut t = tree;
    if start == end {
        t[node] = val;
        return t;
    }
    let mid = (start + end) >> 1;
    if idx <= mid {
        t = seg_update(2 * node, start, mid, idx, val, t);
    } else {
        t = seg_update(2 * node + 1, mid + 1, end, idx, val, t);
    }
    t[node] = seg_min(t[2 * node], t[2 * node + 1]);
    return t;
}

fn create_empty_tree(n: int) -> list {
    let INF = 1000000000;
    let cap = 4 * n + 10;
    let mut t = [];
    let mut i = 0;
    while i < cap {
        t = t + [INF];
        i = i + 1;
    }
    return t;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_segment_tree_tutorial.ltl` validates:

1. **8-Element Array RMQ Verification**:
   - Computes correct subsegment minima across arbitrary intervals ($[0..7]$, $[0..2]$, $[4..7]$, $[1..5]$).
2. **Single-Element Boundary Queries**:
   - Verifies point queries $L = R$.
3. **Dynamic Point Updates**:
   - Mutating element at index 3 and verifying correct propagation through all affected parent intervals.
4. **Single-Element Array Base Case**:
   - Boundary checks with single-element arrays ($n=1$).

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_segment_tree_tutorial.ltl
python -m lateralus_lang check examples/segment_tree_tutorial.ltl
pytest tests/test_compiler.py
```
