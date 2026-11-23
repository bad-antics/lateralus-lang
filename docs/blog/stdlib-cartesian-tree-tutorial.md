---
title: "Linear O(n) Monotonic Stack Construction & RMQ-to-LCA Reduction: Implementing Cartesian Trees in Lateralus"
description: "A comprehensive guide to constructing Cartesian Trees in linear time using monotonic stacks in Lateralus, unifying BST ordering, heap invariants, and Range Minimum Queries."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "data-structures", "trees", "monotonic-stack", "standard-library"]
---

# Linear O(n) Monotonic Stack Construction & RMQ-to-LCA Reduction: Implementing Cartesian Trees in Lateralus

In algorithm engineering and geometric data structures, the **Cartesian Tree**—first introduced by **Jean Vuillemin in 1980**—serves as an indispensable bridge between linear arrays and tree topologies. 

A Cartesian tree over an array $A[0 \dots n-1]$ is uniquely defined by two structural invariants:
1. **Binary Search Tree (BST) Invariant on Indices**: An in-order traversal of the tree visits nodes in exactly their original array index order $(0, 1, \dots, n-1)$.
2. **Min-Heap Invariant on Values**: For every node $u$, the value $A[u]$ is strictly less than or equal to the values of its children $(A[\text{left}(u)]$ and $A[\text{right}(u)])$. Consequently, the root of any subtree rooted at $u$ corresponds to the minimum element within the contiguous index span represented by that subtree.

---

## 1. Mathematical Principles and Properties

### 1.1 The RMQ-to-LCA Equivalence Theorem

A cornerstone result in theoretical computer science states that:
$$\operatorname{RMQ}_A(L, R) = \operatorname{LCA}_{T}(L, R)$$

The index of the minimum element in array slice $A[L \dots R]$ is precisely the **Lowest Common Ancestor (LCA)** of nodes $L$ and $R$ in the Cartesian Tree $T$. This equivalence allows range query problems on flat arrays to be transformed into structural ancestors queries on trees.

```
Array: [9, 3, 7, 1, 8, 12, 10, 20, 15, 18, 5]
Index:  0  1  2  3  4   5   6   7   8   9 10

Cartesian Tree Topology:
                 (1, idx=3) [ROOT]
               /           \
       (3, idx=1)         (5, idx=10)
      /         \         /
  (9, idx=0)  (7, idx=2) (8, idx=4)
                              \
                            (10, idx=6)
                            /         \
                       (12, idx=5)  (15, idx=8)
                                    /         \
                              (20, idx=7)   (18, idx=9)
```

### 1.2 Linear O(n) Monotonic Stack Construction

Rather than recursively searching for the minimum in $O(n^2)$ worst-case time, we build the tree incrementally from left to right using a **monotonic stack**.

The stack maintains the **right spine** of the partially constructed tree (i.e., the path from the current root walking strictly through right children). Since values increase monotonically down the right spine:
1. When inserting element $i$, we pop nodes from the stack that have values greater than $A[i]$.
2. The last node popped was previously on the right spine, has a smaller index than $i$, but a larger value. It becomes the **left child** of $i$.
3. The element remaining on top of the stack (if any) has a smaller value than $A[i]$ and becomes the **parent** of $i$, with $i$ taking its right child slot.
4. Push index $i$ onto the stack.

**Amortized Complexity**: Each node is pushed onto the stack exactly once and popped at most once. Hence, the entire construction runs in strictly **$O(n)$ time** and **$O(n)$ space**.

---

## 2. Implementation in Lateralus

Below is the clean, robust implementation of Cartesian Tree construction in Lateralus:

```lateralus
pub fn build_cartesian_tree(arr, n) {
    let left = dict()
    let right = dict()
    let parent = dict()
    let i = 0
    while i < n {
        left[i] = -1
        right[i] = -1
        parent[i] = -1
        i = i + 1
    }

    let stack = dict()
    let top = 0

    i = 0
    while i < n {
        let last_popped = -1
        while top > 0 && arr[stack[top - 1]] > arr[i] {
            last_popped = stack[top - 1]
            top = top - 1
        }

        if last_popped != -1 {
            left[i] = last_popped
            parent[last_popped] = i
        }

        if top > 0 {
            let p = stack[top - 1]
            right[p] = i
            parent[i] = p
        }

        stack[top] = i
        top = top + 1
        i = i + 1
    }

    let root = -1
    if n > 0 {
        root = stack[0]
    }

    let tree = dict()
    tree["root"] = root
    tree["left"] = left
    tree["right"] = right
    tree["parent"] = parent
    return tree
}
```

---

## 3. Complexity & Structural Invariants

| Invariant | Requirement | Verification Method |
| :--- | :--- | :--- |
| **Time Complexity** | $O(n)$ | Monotonic stack each index pushed/popped $\le 1$ |
| **Space Complexity**| $O(n)$ | Auxiliary left, right, parent, and stack vectors |
| **In-Order Sequence**| $0, 1, \dots, n-1$ | Iterative in-order traversal stack output |
| **Heap Property** | $A[\text{parent}(u)] \le A[u]$ | Direct ancestor inequality check |
| **Root Property** | $A[\text{root}] = \min(A)$ | Validated against global linear minimum |

---

## 4. Verification and Practical Usage

The test suite in `tests/stdlib_cartesian_tree_tutorial.ltl` confirms:
- Classic 11-element permutation with verified in-order sequence and heap invariants
- Monotonically increasing sequences (degenerate right-spine linked list)
- Monotonically decreasing sequences (degenerate left-spine linked list)
- Single-element arrays

A real-world quantitative trading example tracking order book price troughs across intraday time slices is provided in `examples/cartesian_tree_tutorial.ltl`.
