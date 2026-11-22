# Binary Search Tree Tutorial: Node-Based Invariants and In-Order Projections

## Overview

A **Binary Search Tree** (BST) is a hierarchical node-based binary tree data structure where each node stores a key and maintains the fundamental **BST ordering property**:
- The key of every node in the left subtree is strictly less than the node's key:
  $$\forall u \in \text{LeftSubtree}(v): \text{key}(u) < \text{key}(v)$$
- The key of every node in the right subtree is strictly greater than the node's key:
  $$\forall w \in \text{RightSubtree}(v): \text{key}(w) > \text{key}(v)$$

In programming language compilers, runtime systems, and database index architectures, BSTs provide:
- **Symbol Tables & Scope Registries**: Associating identifier strings or variable offsets with $O(h)$ lookup speed.
- **Sorted Sequence Generation**: Yielding ascending linearly sorted sequences via recursive in-order traversal in $O(n)$ time without additional sorting steps.
- **Dynamic Set Membership**: Fast insertion, deletion, and containment verification.

---

## Operations and Complexity

Given a tree of height $h$:

### 1. Key Search: $O(h)$
To search for key $k$:
1. If the current root is `nil`, the key is absent (`false`).
2. If $k == \text{root.val}$, the key is present (`true`).
3. If $k < \text{root.val}$, recursively search `root.left`.
4. Otherwise, recursively search `root.right`.

### 2. Insertion: $O(h)$
To insert key $k$:
- Traverse down the tree following search comparisons until reaching a `nil` link.
- Instantiate and return a new node `bst_new(k)` linked to the appropriate parent pointer.

### 3. Extremum Queries: $O(h)$
- **Minimum**: Follow left child links until `left == nil`.
- **Maximum**: Follow right child links until `right == nil`.

### 4. In-Order Traversal: $O(n)$
Traversing in order:
$$\text{InOrder}(\text{node}) = \text{InOrder}(\text{node.left}) \cup [\text{node.val}] \cup \text{InOrder}(\text{node.right})$$
By induction on the BST invariant, this always produces a monotonically ascending sequence.

---

## Lateralus Implementation

```lateralus
fn bst_new(val: int) -> dict {
    let mut node = {};
    node["val"] = val;
    node["left"] = nil;
    node["right"] = nil;
    return node;
}

fn bst_insert(root: dict, val: int) -> dict {
    if root == nil {
        return bst_new(val);
    }
    let r_val = root["val"];
    if val < r_val {
        root["left"] = bst_insert(root["left"], val);
    } else {
        if val > r_val {
            root["right"] = bst_insert(root["right"], val);
        }
    }
    return root;
}

fn bst_search(root: dict, val: int) -> bool {
    if root == nil {
        return false;
    }
    let r_val = root["val"];
    if val == r_val {
        return true;
    }
    if val < r_val {
        return bst_search(root["left"], val);
    }
    return bst_search(root["right"], val);
}

fn bst_min(root: dict) -> int {
    let mut curr = root;
    while curr["left"] != nil {
        curr = curr["left"];
    }
    return curr["val"];
}

fn bst_max(root: dict) -> int {
    let mut curr = root;
    while curr["right"] != nil {
        curr = curr["right"];
    }
    return curr["val"];
}

fn bst_inorder(root: dict) -> list {
    if root == nil {
        return [];
    }
    let left_list = bst_inorder(root["left"]);
    let right_list = bst_inorder(root["right"]);
    return left_list + [root["val"]] + right_list;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_bst_tutorial.ltl` validates:

1. **Balanced 7-Node BST**:
   - Keys: `[50, 30, 70, 20, 40, 60, 80]`.
   - Successful hits for inner, leaf, and root keys.
   - Successful misses for absent keys (10, 45, 99).
   - In-order traversal matching strictly sorted list `[20, 30, 40, 50, 60, 70, 80]`.
2. **Extremum Verification**:
   - `bst_min` returns 20; `bst_max` returns 80.
3. **Degenerate/Skewed Chains**:
   - Descending chain `5 -> 4 -> 3 -> 2 -> 1` maintaining sorted order.
4. **Single-Node Boundary Conditions**:
   - Isolated single-node trees correctly answer search and extremum queries.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_bst_tutorial.ltl
python -m lateralus_lang check examples/bst_tutorial.ltl
pytest tests/test_compiler.py
```
