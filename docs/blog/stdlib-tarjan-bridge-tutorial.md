---
title: "Linear O(V + E) Undirected Graph Bridge Finding: Implementing Tarjan's Algorithm in Lateralus"
description: "A comprehensive guide to detecting critical bridges and single points of failure in undirected graphs in linear time using Robert Tarjan's DFS low-link algorithm in Lateralus."
date: "2026-11-23"
author: "Lateralus Standard Library Team"
tags: ["algorithms", "graph-theory", "tarjan", "dfs", "standard-library"]
---

# Linear O(V + E) Undirected Graph Bridge Finding: Implementing Tarjan's Algorithm in Lateralus

In graph theory, network survivability, and distributed systems architecture, identifying vulnerabilities before they cause catastrophic partitions is paramount. 

An edge $e = (u, v)$ in a connected undirected graph $G = (V, E)$ is defined as a **Bridge** (or **Cut-Edge**) if removing $e$ strictly increases the number of connected components in $G$. In physical terms, a bridge represents a **Single Point of Failure (SPOF)**: if that link fails, communication between disjoint clusters is severed.

While a naive approach tests each edge by temporary removal in $O(E \cdot (V + E))$ time, **Robert Tarjan (1974)** discovered a landmark algorithm that identifies **all bridges in a single Depth-First Search (DFS) traversal in optimal $O(V + E)$ time**.

---

## 1. Graph Theoretical Foundations

### 1.1 DFS Tree and Edge Classification

During a DFS traversal of an undirected graph starting from an arbitrary root, edges are partitioned into two disjoint categories:
1. **Tree Edges**: Edges that lead to an unvisited vertex during DFS. These form a spanning forest.
2. **Back Edges**: Edges connecting a vertex to one of its already-visited ancestors in the DFS tree (excluding the immediate parent).

Crucially, **no cross-edges exist in undirected DFS trees**.

```
    (0)
   /   \  [Tree Edges]
 (1) - (2) [Back-Edge 2 -> 0]
  |
 (3) [Bridge 1 - 3: No back-edge bypasses it!]
```

### 1.2 DFN and Low-Link Invariants

We define two integer labels for every vertex $u \in V$:
- **Discovery Time ($\operatorname{dfn}[u]$)**: The sequential clock tick at which vertex $u$ is first entered during DFS.
- **Low-Link Value ($\operatorname{low}[u]$)**: The minimum discovery time reachable from $u$ via a sequence of zero or more tree edges followed by at most one back-edge:

$$\operatorname{low}[u] = \min \begin{cases}
\operatorname{dfn}[u] \\
\min_{(u, v) \in \text{Back-Edges}} \operatorname{dfn}[v] \\
\min_{(u, v) \in \text{Tree-Edges}} \operatorname{low}[v]
\end{cases}$$

### 1.3 The Bridge Criterion Theorem

**Theorem**: A tree edge $(u, v)$ (where $u$ is the parent of $v$) is a **bridge** if and only if:
$$\operatorname{low}[v] > \operatorname{dfn}[u]$$

**Proof Intuition**:
- If $\operatorname{low}[v] \le \operatorname{dfn}[u]$, there exists at least one back-edge from the subtree rooted at $v$ reaching $u$ or an ancestor of $u$. Thus, alternative redundant paths exist, and removing $(u, v)$ does not disconnect the graph.
- If $\operatorname{low}[v] > \operatorname{dfn}[u]$, no vertex in the subtree of $v$ can reach any node outside that subtree without passing through $(u, v)$. Hence, removing $(u, v)$ irrevocably isolates the subtree of $v$.

---

## 2. Implementation in Lateralus

Below is the production-grade implementation of Tarjan's Bridge-Finding algorithm in Lateralus, safely skipping immediate parent edges during undirected traversals:

```lateralus
pub fn new_graph(n) {
    let adj = dict()
    let i = 0
    while i < n {
        let list = dict()
        list["len"] = 0
        adj[i] = list
        i = i + 1
    }
    return adj
}

pub fn add_edge(adj, u, v) {
    let l_u = adj[u]
    let sz_u = l_u["len"]
    l_u[sz_u] = v
    l_u["len"] = sz_u + 1

    let l_v = adj[v]
    let sz_v = l_v["len"]
    l_v[sz_v] = u
    l_v["len"] = sz_v + 1
}

pub fn dfs_bridge(u, p, adj, dfn, low, state, bridges) {
    let t = state["timer"] + 1
    state["timer"] = t
    dfn[u] = t
    low[u] = t

    let neighbors = adj[u]
    let deg = neighbors["len"]
    let i = 0
    while i < deg {
        let v = neighbors[i]
        if v == p {
            // Ignore immediate parent edge in undirected traversal
        } else {
            if dfn[v] > 0 {
                // Back-edge to an ancestor
                if dfn[v] < low[u] {
                    low[u] = dfn[v]
                }
            } else {
                // Tree-edge
                dfs_bridge(v, u, adj, dfn, low, state, bridges)
                if low[v] < low[u] {
                    low[u] = low[v]
                }
                // Necessary & sufficient bridge condition
                if low[v] > dfn[u] {
                    let b = dict()
                    if u < v {
                        b["u"] = u
                        b["v"] = v
                    } else {
                        b["u"] = v
                        b["v"] = u
                    }
                    let cnt = state["bridges_cnt"]
                    bridges[cnt] = b
                    state["bridges_cnt"] = cnt + 1
                }
            }
        }
        i = i + 1
    }
}
```

---

## 3. Complexity & Algorithmic Guarantees

| Metric | Complexity | Explanation |
| :--- | :--- | :--- |
| **Time Complexity** | $O(V + E)$ | Every vertex and edge is visited at most twice |
| **Space Complexity**| $O(V + E)$ | Adjacency lists and DFS state vectors (`dfn`, `low`) |
| **Parent Traversal**| Correct | Bypasses reverse path along same undirected edge |
| **Multiple Components**| Supported | Outer loop iterates over all unvisited vertices |

---

## 4. Verification and Practical Usage

The test suite in `tests/stdlib_tarjan_bridge_tutorial.ltl` validates:
- **Dumbbell Graph**: Two 3-node cliques joined by a single central edge `(2, 3)`, correctly isolating exactly one bridge.
- **Cycle Graph**: A 4-cycle containing zero bridges.
- **Tree Topology**: An acyclic tree where every single edge is proven to be a bridge.

A real-world telecommunications backbone network topology analysis identifying trans-Atlantic subsea cable single points of failure is demonstrated in `examples/tarjan_bridge_tutorial.ltl`.
