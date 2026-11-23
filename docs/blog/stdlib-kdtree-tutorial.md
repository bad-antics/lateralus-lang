---
title: "K-Dimensional Spatial Indexing: Implementing KD-Trees & O(log n) Nearest Neighbor Search in Lateralus"
description: "A comprehensive guide to constructing K-Dimensional Trees (KD-Trees) in Lateralus, partitioning multi-dimensional spaces for sub-linear O(log n) Nearest Neighbor Search."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "data-structures", "geometry", "spatial", "standard-library"]
---

# K-Dimensional Spatial Indexing: Implementing KD-Trees & O(log n) Nearest Neighbor Search in Lateralus

In computational geometry, geographic information systems (GIS), robotics lidar point-cloud registration, and machine learning (K-Nearest Neighbors), finding the closest point in a multidimensional metric space to an arbitrary query coordinate is a foundational operation. 

A brute-force scan over $n$ coordinates requires linear $O(n)$ distance computations per query, which is computationally prohibitive when serving thousands of real-time spatial requests per second.

The **K-Dimensional Tree (KD-Tree)**—invented by **Jon Louis Bentley in 1975**—generalizes 1D binary search trees to $k$-dimensional metric spaces. By cyclically alternating partitioning axes at each tree depth, a KD-Tree divides the space into nested hyper-rectangles, accelerating **Nearest Neighbor Search (NNS)** to an expected **sub-linear $O(\log n)$ runtime**.

---

## 1. Geometric Foundations & The Hyperplane Pruning Invariant

### 1.1 Alternating Orthogonal Hyperplanes

In a 2D metric space ($k = 2$), the splitting axis alternates between the X-axis and Y-axis depending on the depth $d$ of the node:
$$\text{axis} = d \bmod 2$$

- At even depths ($\text{axis} = 0$), the plane is partitioned vertically by the line $x = \text{node}.x$.
- At odd depths ($\text{axis} = 1$), the plane is partitioned horizontally by the line $y = \text{node}.y$.

```
          (5, 4) [Split X=5]
         /      \
   (2, 3) [Y=3]   (9, 6) [Y=6]
   /    \         /    \
 (4, 7) (8, 1)  (7, 2)  ...
```

### 1.2 Nearest Neighbor Search & Hyper-Sphere Pruning

During a Nearest Neighbor query at point $Q = (q_x, q_y)$, we maintain the current best candidate point and its squared Euclidean distance $r^2 = \text{best\_dist}$.

1. **Greedy Dive**: Recurse down the tree by comparing $Q$ to the current node along the current axis, choosing the branch that contains $Q$ first.
2. **Backtracking and Pruning Criterion**: Upon unwinding recursion, compute the orthogonal distance from $Q$ to the splitting hyperplane:
   $$\Delta = Q_{\text{axis}} - \text{node}_{\text{axis}}$$
   - **Pruning Rule**: The second (opposite) branch can only contain a closer point if the hypersphere of radius $r$ centered at $Q$ intersects the splitting hyperplane:
   $$\Delta^2 < r^2$$
   - If $\Delta^2 \ge r^2$, the entire opposite subtree lies outside the candidate sphere and is **completely pruned without traversal**.

---

## 2. Implementation in Lateralus

Below is the clean implementation of a 2D KD-Tree with squared Euclidean distance and hyperplane pruning in Lateralus:

```lateralus
pub fn new_kdtree() {
    let tree = dict()
    tree["root"] = -1
    tree["nodes"] = dict()
    tree["count"] = 0
    return tree
}

pub fn dist_sq(x1, y1, x2, y2) {
    let dx = x1 - x2
    let dy = y1 - y2
    return dx * dx + dy * dy
}

pub fn insert_kd_node(tree, curr_id, new_id, depth) {
    if curr_id == -1 {
        return new_id
    }

    let curr = tree["nodes"][curr_id]
    let new_node = tree["nodes"][new_id]
    let axis = depth % 2

    if axis == 0 {
        if new_node["x"] < curr["x"] {
            curr["left"] = insert_kd_node(tree, curr["left"], new_id, depth + 1)
        } else {
            curr["right"] = insert_kd_node(tree, curr["right"], new_id, depth + 1)
        }
    } else {
        if new_node["y"] < curr["y"] {
            curr["left"] = insert_kd_node(tree, curr["left"], new_id, depth + 1)
        } else {
            curr["right"] = insert_kd_node(tree, curr["right"], new_id, depth + 1)
        }
    }

    return curr_id
}

pub fn insert_point(tree, x, y) {
    let id = tree["count"]
    let node = dict()
    node["id"] = id
    node["x"] = x
    node["y"] = y
    node["left"] = -1
    node["right"] = -1

    tree["nodes"][id] = node
    tree["count"] = id + 1
    tree["root"] = insert_kd_node(tree, tree["root"], id, 0)
    return id
}

pub fn search_nn_recursive(tree, curr_id, qx, qy, depth, best) {
    if curr_id == -1 {
        return 0
    }

    let curr = tree["nodes"][curr_id]
    let d = dist_sq(curr["x"], curr["y"], qx, qy)

    if d < best["dist"] {
        best["dist"] = d
        best["best_id"] = curr_id
        best["best_x"] = curr["x"]
        best["best_y"] = curr["y"]
    }

    let axis = depth % 2
    let diff = 0
    let first_branch = -1
    let second_branch = -1

    if axis == 0 {
        diff = qx - curr["x"]
        if diff < 0 {
            first_branch = curr["left"]
            second_branch = curr["right"]
        } else {
            first_branch = curr["right"]
            second_branch = curr["left"]
        }
    } else {
        diff = qy - curr["y"]
        if diff < 0 {
            first_branch = curr["left"]
            second_branch = curr["right"]
        } else {
            first_branch = curr["right"]
            second_branch = curr["left"]
        }
    }

    // 1. Visit closer sub-space
    search_nn_recursive(tree, first_branch, qx, qy, depth + 1, best)

    // 2. Prune opposite sub-space if hypersphere doesn't cross boundary
    if diff * diff < best["dist"] {
        search_nn_recursive(tree, second_branch, qx, qy, depth + 1, best)
    }

    return 0
}

pub fn find_nearest_neighbor(tree, qx, qy) {
    let best = dict()
    best["dist"] = 2000000000
    best["best_id"] = -1
    best["best_x"] = 0
    best["best_y"] = 0

    search_nn_recursive(tree, tree["root"], qx, qy, 0, best)
    return best
}
```

---

## 3. Complexity & Performance Profile

| Operation | Average Case | Worst Case (Degenerate) | Space Complexity |
| :--- | :--- | :--- | :--- |
| `insert_point(tree, x, y)` | $O(\log n)$ | $O(n)$ | $O(1)$ per node |
| `find_nearest_neighbor(tree, qx, qy)` | $O(\log n)$ | $O(n)$ | $O(\log n)$ recursion stack |
| Metric Distance Formula | Exact $O(1)$ | Exact $O(1)$ | No floating-point drift |

---

## 4. Verification and Practical Applications

The verification suite in `tests/stdlib_kdtree_tutorial.ltl` checks:
- Standard 6-point 2D dataset with multi-target nearest neighbor queries
- Points across negative and positive Cartesian quadrants
- Single-point boundary conditions

A real-world municipal 911 emergency vehicle response station dispatch simulation is provided in `examples/kdtree_tutorial.ltl`.
