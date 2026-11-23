---
title: "Augmenting Binary Search Trees with Subtree Max-High: Implementing Interval Trees in Lateralus"
description: "A comprehensive guide to implementing Interval Trees (CLRS 14.3) in Lateralus, maintaining subtree max-high coordinates to enable O(log n) overlap queries."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "data-structures", "trees", "intervals", "standard-library"]
---

# Augmenting Binary Search Trees with Subtree Max-High: Implementing Interval Trees in Lateralus

In computer systems, geometric modeling, and resource scheduling, managing collections of dynamic one-dimensional intervals $[t_{\text{low}}, t_{\text{high}}]$ is a ubiquitous requirement. Whether detecting meeting room collisions, computing overlapping windows in time-series telemetry, or optimizing register allocation in compilers via live-range analysis, scanning $n$ intervals naively costs $O(n)$ per query.

By **augmenting a Binary Search Tree (BST)**—as formalized in *Introduction to Algorithms (CLRS, Chapter 14.3)*—we can store dynamic intervals such that inserting, deleting, and querying for any overlapping interval executes in strictly **logarithmic $O(\log n)$ time**.

---

## 1. Mathematical Mechanics & Augmentation Invariants

An Interval Tree represents each closed interval $i = [\text{low}, \text{high}]$ as a tree node. It maintains two core invariants:

1. **BST Key Invariant**: The tree is organized as a binary search tree ordered by the left endpoint ($i.\text{low}$).
2. **Subtree Max-High Augmentation**: Each node $x$ stores an additional scalar attribute $x.\text{max\_high}$, defined as the maximum of all interval right endpoints within the subtree rooted at $x$:

$$x.\text{max\_high} = \max \left( x.\text{high}, \;\; \text{left}(x).\text{max\_high}, \;\; \text{right}(x).\text{max\_high} \right)$$

```
                    [15, 20] (max_high = 40)
                   /                        \
        [10, 30] (max_high = 30)       [17, 19] (max_high = 40)
       /          \                                \
 [5, 20] (20)   [12, 15] (15)                   [30, 40] (40)
```

### 1.1 Overlap Criterion

Two closed intervals $i = [l_1, h_1]$ and $j = [l_2, h_2]$ overlap if and only if:
$$l_1 \le h_2 \quad \text{and} \quad l_2 \le h_1$$

### 1.2 The Logarithmic Search Pruning Theorem

To find an interval in the tree that overlaps query $q = [q_{\text{low}}, q_{\text{high}}]$, we traverse from the root:

1. If node $x$ overlaps $q$, return $x$ immediately.
2. If $x.\text{left} \ne \text{nil}$ and $x.\text{left}.\text{max\_high} \ge q_{\text{low}}$, **traverse into the left subtree**.
3. Otherwise, **traverse into the right subtree**.

**Proof of Correctness (CLRS Theorem 14.2)**:
- **Case 1 (Going Left)**: If $x.\text{left}.\text{max\_high} \ge q_{\text{low}}$, there exists some interval $i$ in the left subtree with $i.\text{high} \ge q_{\text{low}}$. 
  - If $i$ overlaps $q$, going left is guaranteed to succeed.
  - If $i$ does not overlap $q$, then $i.\text{low} > q_{\text{high}}$. Because the tree is a BST on $\text{low}$, every interval in the right subtree must also have $\text{low} \ge x.\text{low} \ge i.\text{low} > q_{\text{high}}$, which means **no interval in the right subtree can possibly overlap $q$**. Thus, search can safely prune the right subtree.
- **Case 2 (Going Right)**: If $x.\text{left}.\text{max\_high} < q_{\text{low}}$, then every interval $j$ in the left subtree has $j.\text{high} < q_{\text{low}}$, meaning no interval in the left subtree overlaps $q$. Search can safely prune the left subtree.

---

## 2. Implementation in Lateralus

Below is the robust implementation of an Interval Tree with dynamic $\text{max\_high}$ propagation:

```lateralus
pub fn new_interval_tree() {
    let tree = dict()
    tree["root"] = -1
    tree["nodes"] = dict()
    tree["count"] = 0
    return tree
}

pub fn intervals_overlap(l1, h1, l2, h2) {
    if l1 <= h2 && l2 <= h1 { return 1 }
    return 0
}

pub fn update_max_high(tree, node_id) {
    let node = tree["nodes"][node_id]
    let m = node["high"]
    let l = node["left"]
    if l != -1 {
        let l_max = tree["nodes"][l]["max_high"]
        if l_max > m { m = l_max }
    }
    let r = node["right"]
    if r != -1 {
        let r_max = tree["nodes"][r]["max_high"]
        if r_max > m { m = r_max }
    }
    node["max_high"] = m
}

pub fn insert_interval(tree, low, high) {
    let id = tree["count"]
    let node = dict()
    node["id"] = id
    node["low"] = low
    node["high"] = high
    node["max_high"] = high
    node["left"] = -1
    node["right"] = -1

    tree["nodes"][id] = node
    tree["count"] = id + 1
    tree["root"] = insert_node(tree, tree["root"], id)
    return id
}

pub fn search_overlap(tree, q_low, q_high) {
    let curr_id = tree["root"]
    while curr_id != -1 {
        let node = tree["nodes"][curr_id]
        if intervals_overlap(node["low"], node["high"], q_low, q_high) == 1 {
            return curr_id
        }

        let l_id = node["left"]
        if l_id != -1 && tree["nodes"][l_id]["max_high"] >= q_low {
            curr_id = l_id
        } else {
            curr_id = node["right"]
        }
    }
    return -1
}
```

---

## 3. Complexity & Performance Invariants

| Operation | Time Complexity | Auxiliary Space |
| :--- | :--- | :--- |
| `insert_interval(tree, l, h)` | $O(\log n)$ | $O(1)$ per node |
| `search_overlap(tree, q_l, q_h)` | $O(\log n)$ | $O(1)$ |
| `update_max_high(tree, node)` | $O(1)$ | $O(1)$ |
| Total Storage | $O(n)$ | Linear memory footprint |

---

## 4. Verification and Practical Usage

The test suite in `tests/stdlib_interval_tree_tutorial.ltl` checks:
- The standard 6-interval CLRS test suite with multi-interval overlap coverage
- Exact point-boundary touching ($[10, 20]$ vs $[20, 25]$)
- Disjoint gap queries returning `-1`
- Single-interval base cases

A real-world executive meeting room calendar reservation collision detection system is demonstrated in `examples/interval_tree_tutorial.ltl`.
