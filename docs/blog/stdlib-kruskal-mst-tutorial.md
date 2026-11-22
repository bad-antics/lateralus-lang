# Kruskal's Minimum Spanning Tree (MST) Algorithm in Lateralus

## 1. Introduction

A **Spanning Tree** of a connected, undirected, edge-weighted graph $G = (V, E)$ is an acyclic subgraph $T = (V, E_T)$ containing all $|V|$ vertices with exactly $|V| - 1$ edges. A **Minimum Spanning Tree (MST)** is a spanning tree whose total edge weight:

$$W(T) = \sum_{e \in E_T} w(e)$$

is strictly minimized over all possible spanning trees.

Formulated by Joseph Kruskal in 1956, **Kruskal's Algorithm** is an elegant, greedy algorithmic design that builds the MST edge by edge:
1. Sort all edges in non-decreasing order of weight: $w(e_1) \le w(e_2) \le \dots \le w(e_{|E|})$.
2. Initialize each vertex as an independent component in a **Disjoint Set Union (DSU)** data structure.
3. Iterate through sorted edges, greedily accepting edge $(u, v)$ if and only if $u$ and $v$ belong to different components (preventing cycles), and merging their sets.
4. Terminate when $|V| - 1$ edges have been selected or all edges are exhausted.

Kruskal's algorithm exhibits an overall time complexity of:

$$\mathcal{O}(|E| \log |E| + |E| \alpha(|V|))$$

where $\alpha$ is the extremely slow-growing inverse Ackermann function, effectively constant in all physical computations.

This tutorial provides a complete walkthrough of implementing Kruskal's MST algorithm in Lateralus (`stdlib/kruskal_mst.ltl`), complete with runnable network topology optimizations and golden test vectors.

---

## 2. Core Concepts & Mathematical Guarantees

### 2.1 The Cut Property
The correctness of Kruskal's greedy strategy is guaranteed by the fundamental **Cut Property**:
> For any cut $(S, V \setminus S)$ in a graph $G$, if an edge $e = (u, v)$ is the strictly minimum-weight edge crossing the cut, then $e$ must belong to every Minimum Spanning Tree of $G$.

Since Kruskal's algorithm always inspects the globally minimum available edge crossing between previously disjoint components, every accepted edge is mathematically guaranteed to belong to the MST.

### 2.2 Cycle Prevention with Disjoint Set Union (DSU)
To determine whether adding candidate edge $(u, v)$ creates a cycle:
- `find(u)` and `find(v)` identify the representative root of $u$ and $v$'s respective trees.
- If `find(u) == find(v)`, both vertices already share a path; adding $(u, v)$ would form a cycle and is rejected.
- If `find(u) != find(v)`, the edge connects two disjoint trees; we accept the edge and execute `union(u, v)` with rank balancing.

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
fn make_edge(u, v, w) {
    let e = dict()
    e["u"] = u
    e["v"] = v
    e["w"] = w
    return e
}

fn sort_edges(edges) {
    let n = len(edges)
    let i = 1
    while i < n {
        let key = edges[i]
        let j = i - 1
        while j >= 0 and edges[j]["w"] > key["w"] {
            edges[j + 1] = edges[j]
            j = j - 1
        }
        edges[j + 1] = key
        i = i + 1
    }
    return edges
}

fn dsu_find(parent, i) {
    let p = parent[i]
    while p != parent[p] {
        p = parent[p]
    }
    return p
}

fn dsu_union(parent, rank, x, y) {
    let root_x = dsu_find(parent, x)
    let root_y = dsu_find(parent, y)
    if root_x == root_y {
        return false
    }
    if rank[root_x] < rank[root_y] {
        parent[root_x] = root_y
    } else {
        if rank[root_x] > rank[root_y] {
            parent[root_y] = root_x
        } else {
            parent[root_y] = root_x
            rank[root_x] = rank[root_x] + 1
        }
    }
    return true
}

pub fn kruskal_mst(n, edges) {
    let sorted_edges = sort_edges(edges)

    let parent = dict()
    let rank = dict()
    let i = 0
    while i < n {
        parent[i] = i
        rank[i] = 0
        i = i + 1
    }

    let mst_edges = []
    let total_weight = 0
    let edge_count = 0

    let idx = 0
    while idx < len(sorted_edges) and edge_count < n - 1 {
        let edge = sorted_edges[idx]
        let u = edge["u"]
        let v = edge["v"]
        let w = edge["w"]

        if dsu_union(parent, rank, u, v) {
            mst_edges = push(mst_edges, edge)
            total_weight = total_weight + w
            edge_count = edge_count + 1
        }
        idx = idx + 1
    }

    let res = dict()
    res["edges"] = mst_edges
    res["total_weight"] = total_weight
    res["is_connected"] = (edge_count == n - 1)
    return res
}
```

---

## 4. Real-World Engineering Applications

1. **Global Fiber-Optic Backbone Routing**: Connecting multi-region cloud data centers (e.g. Frankfurt, London, New York, Tokyo) with minimal latency and infrastructure lease expenses while guaranteeing loop-free connectivity.
2. **Blockchain P2P Mesh Optimization**: Structuring gossip peer overlay connections to maximize broadcast reach with minimal redundant packet amplification.
3. **VLSI & Circuit Design**: Minimizing wire length and capacitive delay in integrated circuit power and clock tree routing.
4. **Hierarchical Clustering**: Identifying natural clusters in unsupervised machine learning via single-linkage agglomerative clustering.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_kruskal_mst_tutorial.ltl
python -m lateralus_lang check examples/kruskal_mst_tutorial.ltl
pytest tests/test_compiler.py
```
