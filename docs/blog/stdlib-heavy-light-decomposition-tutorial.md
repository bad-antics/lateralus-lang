---
title: "Heavy-Light Decomposition (HLD): Transforming Tree Paths to O(log^2 n) Array Intervals in Lateralus"
description: "A comprehensive guide to Heavy-Light Decomposition in Lateralus, partitioning trees into logarithmic heavy chains for O(log^2 n) path modifications and queries."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "graph-theory", "trees", "hld", "standard-library"]
---

# Heavy-Light Decomposition (HLD): Transforming Tree Paths to O(log^2 n) Array Intervals in Lateralus

In computer networks, 3D skeletal rigging, and distributed database routing, trees frequently serve as the foundational backbone for hierarchical data. However, performing dynamic modifications (such as updating weights along a path between arbitrary nodes $u$ and $v$ or querying path aggregates) naively takes $O(n)$ time.

**Heavy-Light Decomposition (HLD)**—invented by **Daniel Sleator and Robert Tarjan in 1983**—solves this bottleneck by partitioning the vertices of any rooted tree into a set of disjoint linear paths called **Heavy Chains**. 

When mapped through an in-order DFS indexing traversal, each heavy chain corresponds to a **contiguous interval in a 1D array**. As a result:
1. Any arbitrary path between vertices $u$ and $v$ decomposes into at most **$O(\log n)$ contiguous intervals**.
2. Combined with a 1D Segment Tree or Fenwick Tree, path updates and path queries run in strictly **$O(\log^2 n)$ time**.
3. Subtree queries run in strictly **$O(\log n)$ time** (since any subtree forms a single contiguous interval $[ \operatorname{dfn}[u], \operatorname{dfn}[u] + \operatorname{sz}[u] - 1 ]$).

---

## 1. Mathematical Mechanics & The Logarithmic Bound

### 1.1 Edge Classification and Subtree Sizes

Let $T$ be a tree rooted at $r$ with $n$ vertices. For any non-leaf vertex $u$:
- **Heavy Child ($\operatorname{hc}(u)$)**: The child $v$ of $u$ with the strictly greatest subtree size $\operatorname{sz}[v]$. (If multiple children share the maximum size, pick one arbitrarily).
- **Heavy Edge**: The directed tree edge $(u, \operatorname{hc}(u))$.
- **Light Edge**: Any directed tree edge $(u, w)$ where $w \ne \operatorname{hc}(u)$.

A maximal sequence of connected heavy edges forms a **Heavy Chain**. Each vertex in the tree belongs to exactly one heavy chain.

```
          (0) [Root, Top=0]
         /   \  [Heavy edge to 1]
    [L] (2)   (1) [Top=0]
       /     /   \  [Heavy edge to 4]
     (5)   (3)   (4) [Top=0]
                  |  [Heavy edge to 6]
                 (6) [Top=0]
```

### 1.2 The Light-Edge Count Theorem

**Theorem**: For any vertex $u$, the path from $u$ to the root traverses at most $\lfloor \log_2 n \rfloor$ light edges.

**Proof**:
Suppose $(p, v)$ is a light edge traversed on the path from $u$ to the root. By definition, $p$ has a heavy child $w$ with $\operatorname{sz}[w] \ge \operatorname{sz}[v]$. 
Thus:
$$\operatorname{sz}[p] > \operatorname{sz}[v] + \operatorname{sz}[w] \ge 2 \cdot \operatorname{sz}[v]$$
Every time a light edge is climbed, the subtree size at least doubles:
$$\operatorname{sz}[p] \ge 2 \cdot \operatorname{sz}[v]$$
Since $\operatorname{sz}[\text{root}] = n$, one can double the subtree size at most $\lfloor \log_2 n \rfloor$ times. 

**Corollary**: Any tree path between two arbitrary vertices $u$ and $v$ crosses at most $2 \lfloor \log_2 n \rfloor$ light edges, meaning the path is partitioned into at most $O(\log n)$ contiguous heavy chain segments.

---

## 2. Two-Pass DFS Architecture

HLD is synthesized via two clean DFS sweeps:

### 2.1 DFS 1: Subtree Sizes, Depths, and Heavy Children
Computes for every node $u$:
- `parent[u]`: immediate ancestor
- `depth[u]`: distance from root
- `sz[u]`: total vertices in subtree
- `heavy_child[u]`: child maximizing `sz[v]`

### 2.2 DFS 2: Chain Top Assignment and Contiguous DFN Ordering
Traverses the tree to assign 1D array indices `dfn[u]`:
- **Crucial Rule**: Always recurse on `heavy_child[u]` **first** with `top[heavy_child[u]] = top[u]`.
- This invariant guarantees that all vertices along the same heavy chain receive **strictly consecutive integers** in `dfn`.
- For light children $v$, start a new chain header: `top[v] = v`.

---

## 3. Implementation in Lateralus

```lateralus
pub fn dfs1(u, p, d, adj, parent, depth, sz, heavy_child) {
    parent[u] = p
    depth[u] = d
    sz[u] = 1
    heavy_child[u] = -1

    let max_sub = 0
    let neighbors = adj[u]
    let deg = neighbors["len"]
    let i = 0
    while i < deg {
        let v = neighbors[i]
        if v != p {
            dfs1(v, u, d + 1, adj, parent, depth, sz, heavy_child)
            sz[u] = sz[u] + sz[v]
            if sz[v] > max_sub {
                max_sub = sz[v]
                heavy_child[u] = v
            }
        }
        i = i + 1
    }
}

pub fn dfs2(u, chain_top, adj, parent, heavy_child, dfn, rnk, top, state) {
    let t = state["timer"] + 1
    state["timer"] = t
    dfn[u] = t
    rnk[t] = u
    top[u] = chain_top

    let hc = heavy_child[u]
    if hc != -1 {
        dfs2(hc, chain_top, adj, parent, heavy_child, dfn, rnk, top, state)
    }

    let neighbors = adj[u]
    let deg = neighbors["len"]
    let i = 0
    while i < deg {
        let v = neighbors[i]
        if v != parent[u] && v != hc {
            dfs2(v, v, adj, parent, heavy_child, dfn, rnk, top, state)
        }
        i = i + 1
    }
}
```

### 3.1 Path Decomposition & LCA

```lateralus
pub fn get_lca(hld, u, v) {
    let top = hld["top"]
    let depth = hld["depth"]
    let parent = hld["parent"]
    let curr_u = u
    let curr_v = v

    while top[curr_u] != top[curr_v] {
        if depth[top[curr_u]] < depth[top[curr_v]] {
            let tmp = curr_u
            curr_u = curr_v
            curr_v = tmp
        }
        curr_u = parent[top[curr_u]]
    }

    if depth[curr_u] < depth[curr_v] { return curr_u }
    return curr_v
}
```

---

## 4. Complexity & Guarantees

| Operation | Time Complexity | Auxiliary Space |
| :--- | :--- | :--- |
| `build_hld(adj, n, root)` | $O(V)$ | $O(V)$ |
| `get_lca(hld, u, v)` | $O(\log V)$ | $O(1)$ |
| `decompose_path(hld, u, v)`| $O(\log V)$ segments | $O(\log V)$ |
| Subtree Interval Query | $O(1)$ lookup $[ \text{dfn}, \text{dfn}+\text{sz}-1 ]$ | $O(1)$ |

---

## 5. Verification and Practical Applications

The suite in `tests/stdlib_heavy_light_decomposition_tutorial.ltl` verifies:
- Multi-branch 7-node tree with validated subtree sizes and heavy child selections
- DFN continuity checks ensuring $0 \to 1 \to 4 \to 6$ receive consecutive array indices
- LCA accuracy across different heavy chains and parent-child relations
- Linear chain degenerate trees

An enterprise organizational authority escalation simulation is provided in `examples/heavy_light_decomposition_tutorial.ltl`.
