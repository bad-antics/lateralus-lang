# Prim-Jarník Minimum Spanning Tree (MST) Algorithm in Lateralus

## 1. Introduction

A **Minimum Spanning Tree (MST)** of an undirected, edge-weighted graph $G = (V, E)$ is a subset of edges $E_T \subseteq E$ connecting all $|V|$ vertices without forming any cycles, while minimizing the total sum of edge weights:

$$W(T) = \sum_{e \in E_T} w(e)$$

First developed by Czech mathematician Vojtěch Jarník in 1930 and independently rediscovered by Robert C. Prim in 1957 and Edsger W. Dijkstra in 1959, **Prim's Algorithm** is an optimal, vertex-centric greedy algorithm for finding MSTs.

### Prim vs Kruskal: Dual Philosophies
1. **Kruskal's Algorithm** (Edge-Centric): Sorts all edges globally and repeatedly merges disconnected forests using a Disjoint Set Union (DSU) data structure. Complexity: $\mathcal{O}(|E| \log |E|)$, excelling on **sparse graphs** ($|E| \ll |V|^2$).
2. **Prim's Algorithm** (Vertex-Centric): Starts from an arbitrary seed vertex and continuously expands a single contiguous tree by greedily pulling in the closest outside vertex across the tree boundary cut. Complexity with an adjacency matrix: $\mathcal{O}(|V|^2)$, excelling on **dense graphs** ($|E| \approx |V|^2$) where sorting edges would incur heavy overhead.

This tutorial provides a complete implementation of the Prim-Jarník algorithm in Lateralus (`stdlib/prim_mst.ltl`), complete with power grid transmission cabling examples and golden test vectors.

---

## 2. Core Concepts & Cut Property

### 2.1 The Cut Property & Invariants
At each step $k$, let $S \subset V$ denote the set of vertices already incorporated into the growing tree, and $V \setminus S$ denote the unvisited vertices. The pair $(S, V \setminus S)$ defines a **cut** across the graph.

> **Cut Property**: Let $(S, V \setminus S)$ be any cut in $G$. If edge $e = (u, v)$ is the lightest edge with $u \in S$ and $v \in V \setminus S$, then $e$ must be part of a Minimum Spanning Tree of $G$.

Prim's algorithm maintains this invariant strictly:
- For every vertex $v \in V \setminus S$, `key[v]` stores the minimum weight among all edges connecting $v$ to any vertex in $S$.
- In each round, we greedily pick $u = \arg\min_{v \notin S} \text{key}[v]$, add $u$ to $S$, and update the `key` values of $u$'s neighbors.

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
fn init_matrix(n, default_val) {
    let m = dict()
    let i = 0
    while i < n {
        let row = dict()
        let j = 0
        while j < n {
            row[j] = default_val
            j = j + 1
        }
        m[i] = row
        i = i + 1
    }
    return m
}

fn add_undirected_edge(matrix, u, v, w) {
    matrix[u][v] = w
    matrix[v][u] = w
}

pub fn prim_mst(n, matrix) {
    let in_mst = dict()
    let key = dict()
    let parent = dict()

    let i = 0
    while i < n {
        in_mst[i] = false
        key[i] = 999999999
        parent[i] = -1
        i = i + 1
    }

    key[0] = 0

    let count = 0
    let step = 0
    while step < n {
        let min_val = 999999999
        let u = -1
        let v_idx = 0
        while v_idx < n {
            if not in_mst[v_idx] and key[v_idx] < min_val {
                min_val = key[v_idx]
                u = v_idx
            }
            v_idx = v_idx + 1
        }

        if u == -1 {
            step = n
        } else {
            in_mst[u] = true
            count = count + 1

            let v = 0
            while v < n {
                let weight = matrix[u][v]
                if weight > 0 and not in_mst[v] and weight < key[v] {
                    key[v] = weight
                    parent[v] = u
                }
                v = v + 1
            }
            step = step + 1
        }
    }

    let total_weight = 0
    let mst_edges = []
    let is_connected = (count == n)

    if is_connected {
        let idx = 1
        while idx < n {
            total_weight = total_weight + key[idx]
            let edge = dict()
            edge["u"] = parent[idx]
            edge["v"] = idx
            edge["w"] = key[idx]
            mst_edges = push(mst_edges, edge)
            idx = idx + 1
        }
    }

    let res = dict()
    res["total_weight"] = total_weight
    res["edges"] = mst_edges
    res["is_connected"] = is_connected
    return res
}
```

---

## 4. Real-World Engineering Applications

1. **Municipal Electrical Power Distribution**: Designing high-voltage transmission grids connecting generation plants, industrial centers, and residential substations with minimal cabling distance and copper resistance.
2. **Network Spanning Tree Protocol (STP / IEEE 802.1D)**: Preventing bridge loops in Ethernet switched networks by maintaining an active loop-free spanning tree.
3. **Telecommunication Fiber Meshes**: Routing underground fiber backbones connecting dense metropolitan cell towers.
4. **Civil Engineering Pipeline Layout**: Minimizing pipe installation costs for regional water supply and natural gas distribution.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_prim_mst_tutorial.ltl
python -m lateralus_lang check examples/prim_mst_tutorial.ltl
pytest tests/test_compiler.py
```
