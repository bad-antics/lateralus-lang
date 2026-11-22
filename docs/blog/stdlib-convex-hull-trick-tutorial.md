---
title: "Dynamic Envelope Optimization: Implementing Li Chao Segment Trees (CHT) in Lateralus"
description: "A comprehensive guide to implementing the Li Chao Tree (Convex Hull Trick) in Lateralus for dynamic line insertions and logarithmic O(log C) upper envelope queries."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "geometry", "dynamic-programming", "convex-hull", "standard-library"]
---

# Dynamic Envelope Optimization: Implementing Li Chao Segment Trees (CHT) in Lateralus

In computational economics (energy grid marginal cost frontiers), financial algorithmic trading (piecewise linear revenue envelope optimization), and dynamic programming (DP slope optimization), calculating the maximum or minimum value across a dynamic set of linear functions $y = mx + c$ at any coordinate $x$ is a central optimization primitive.

Traditional **Convex Hull Trick (CHT)** algorithms maintain upper/lower hulls using monotonic stacks or dual-pointer deques. However, classical CHT requires slopes $m$ or query positions $x$ to arrive in strictly sorted monotonic order; when lines arrive arbitrarily, maintaining the hull requires complex balanced search trees of lines (like `std::set` with iterator angle comparisons).

The **Li Chao Segment Tree**—introduced by **Li Chao** in 2013—provides a remarkably elegant and general solution:
- **No Monotonicity Required**: Supports arbitrary slopes and query coordinates in any order.
- **Logarithmic Insertion**: Inserts a new line $y = mx + c$ in strictly $O(\log C)$ time over domain $[0, C]$.
- **Logarithmic Evaluation**: Queries the optimal envelope value at any $x_0$ in strictly $O(\log C)$ time.
- **Cache-Friendly Structure**: Employs standard segment tree array indexing ($2u, 2u+1$) without dynamic pointer rebalancing.

---

## 1. Midpoint Dominance & The Loser Descent Theorem

Consider an interval $[l, r]$ with integer midpoint:

$$m = \left\lfloor \frac{l + r}{2} \right\rfloor$$

### 1.1 The Midpoint Invariant

> **Invariant**: Each node $u$ covering interval $[l, r]$ stores the line that achieves the **strictly greatest value at the midpoint** $m$:
> $$\text{stored\_line}(m) \ge \text{candidate\_line}(m)$$

### 1.2 The Loser Descent Theorem

Because two non-parallel straight lines $L_1(x) = m_1 x + c_1$ and $L_2(x) = m_2 x + c_2$ intersect at at most one point:

1. When inserting a new line $L_{\text{new}}$ into a node with existing line $L_{\text{curr}}$, evaluate both at $m$.
2. If $L_{\text{new}}(m) > L_{\text{curr}}(m)$, $L_{\text{new}}$ becomes the dominant line at $m$, and we swap them so that $L_{\text{new}}$ is now the "loser" line.
3. The loser line can now only surpass the winner on **at most one side** of $m$:
   - If $L_{\text{new}}(l) > L_{\text{winner}}(l)$, the loser line must dominate on the left half $[l, m]$. We recurse into the left child ($2u$).
   - If $L_{\text{new}}(r) > L_{\text{winner}}(r)$, the loser line must dominate on the right half $[m+1, r]$. We recurse into the right child ($2u+1$).
   - If neither condition holds, the loser line is completely dominated over the entire interval $[l, r]$ and is pruned.

Because the search interval $[l, r]$ is halved at each step, insertion terminates in strictly $\lceil \log_2(C) \rceil$ levels.

```
       L1: Winner at Midpoint m (Stored in Node)
               \             /
                \     m     /
                 \    |    /
                  \   |   /  <-- Intersection
                   \  |  /
                    \ | /
                     \|/
                      x
       L2: Loser at Midpoint m (Descends to Left Child)
```

---

## 2. Lateralus Implementation

Here is the clean implementation of `stdlib/convex_hull_trick.ltl`:

```lateralus
pub fn new_cht(max_coord) {
    let tree = dict()
    tree["max_coord"] = max_coord
    tree["lines"] = dict()
    return tree
}

pub fn make_line(m, c) {
    let line = dict()
    line["m"] = m
    line["c"] = c
    return line
}

pub fn eval_line(line, x) {
    if line == nil {
        return 0 - 999999999
    }
    return line["m"] * x + line["c"]
}

pub fn cht_insert(tree, u, l, r, new_line) {
    if tree["lines"][u] == nil {
        tree["lines"][u] = new_line
        return true
    }

    let mid = (l + r) / 2
    let new_mid = eval_line(new_line, mid)
    let curr_mid = eval_line(tree["lines"][u], mid)

    if new_mid > curr_mid {
        let temp = tree["lines"][u]
        tree["lines"][u] = new_line
        new_line = temp
    }

    if l == r {
        return true
    }

    let new_left = eval_line(new_line, l)
    let curr_left = eval_line(tree["lines"][u], l)
    if new_left > curr_left {
        cht_insert(tree, 2 * u, l, mid, new_line)
        return true
    }

    let new_right = eval_line(new_line, r)
    let curr_right = eval_line(tree["lines"][u], r)
    if new_right > curr_right {
        cht_insert(tree, 2 * u + 1, mid + 1, r, new_line)
        return true
    }

    return true
}

pub fn cht_add_line(tree, m, c) {
    let line = make_line(m, c)
    let max_c = tree["max_coord"]
    cht_insert(tree, 1, 0, max_c, line)
    return true
}

pub fn cht_query(tree, u, l, r, x) {
    let ans = eval_line(tree["lines"][u], x)
    if l == r {
        return ans
    }

    let mid = (l + r) / 2
    if x <= mid {
        let child_ans = cht_query(tree, 2 * u, l, mid, x)
        if child_ans > ans {
            ans = child_ans
        }
    } else {
        let child_ans = cht_query(tree, 2 * u + 1, mid + 1, r, x)
        if child_ans > ans {
            ans = child_ans
        }
    }
    return ans
}

pub fn cht_get_max(tree, x) {
    let max_c = tree["max_coord"]
    return cht_query(tree, 1, 0, max_c, x)
}
```

---

## 3. Practical Application: Energy Grid Tiered Production Profit Envelope

In deregulated power grids, generating assets (Solar arrays, Gas peaker units, Nuclear baseload) compete to supply demand under variable feed-in tariffs:

```lateralus
pub fn run_energy_tariff_pipeline() {
    let grid_market = new_cht(100)

    // Strategy 1 (Solar & Storage): Revenue = 15*x + 200
    cht_add_line(grid_market, 15, 200)

    // Strategy 2 (Peaker Gas Plant): Revenue = 40*x - 300
    cht_add_line(grid_market, 40, 0 - 300)

    // Strategy 3 (Nuclear Baseload): Revenue = 5*x + 800
    cht_add_line(grid_market, 5, 800)

    // Optimal Tariff Revenue at different load points in O(log C):
    let rev_at_10 = cht_get_max(grid_market, 10)  // Nuclear dominates
    let rev_at_30 = cht_get_max(grid_market, 30)  // Solar/Storage envelope
    let rev_at_80 = cht_get_max(grid_market, 80)  // Peaker Gas plant dominates
}
```

---

## 4. Verification & Testing

The verification test suite in `tests/stdlib_convex_hull_trick_tutorial.ltl` validates:
1. **Single Line Evaluator**: Line $y = 3x + 10$ calculates exact linear steps across $x \in \{0, 5, 10\}$.
2. **Three-Way Intersection Invariance**: Evaluates intersecting lines $y = 2x + 1$, $y = 5x - 5$, and $y = -x + 20$, ensuring the tree returns exact peak envelope values across disjoint domains ($x=0 \to 20$, $x=2 \to 18$, $x=5 \to 20$, $x=10 \to 45$).

Execute the test suite with:

```bash
lateralus check tests/stdlib_convex_hull_trick_tutorial.ltl
lateralus check examples/convex_hull_trick_tutorial.ltl
pytest tests/test_compiler.py
```
