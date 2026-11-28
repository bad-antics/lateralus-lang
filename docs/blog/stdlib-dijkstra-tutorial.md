# Dijkstra's Algorithm Tutorial: Single-Source Shortest Paths and Edge Relaxation

## Overview

Edsger W. Dijkstra's shortest-path algorithm is one of the foundational graph algorithms in computer science and network routing. It computes the single-source shortest path (SSSP) from a starting vertex to all other vertices in a directed or undirected graph with non-negative edge weights.

In Lateralus, Dijkstra's algorithm serves as the computational core for:
- Routing and path-finding protocols (e.g. OSPF, IS-IS link-state routing).
- Transportation networks and supply-chain logistics optimization.
- Transaction dependency resolution and gas-optimal state propagation in distributed ledgers.

This tutorial demonstrates the implementation of Dijkstra's algorithm in Lateralus, edge relaxation invariants, unreachable component safety, and deterministic path reconstruction.

---

## Algorithm Mechanics

Dijkstra's algorithm maintains three state vectors across an $n$-vertex graph:
1. `dist`: An array storing the current minimum known cost from the source vertex to each vertex $v$. Initialized to $\infty$ (`INF`), with `dist[source] = 0`.
2. `visited`: A boolean array indicating whether the definitive shortest distance to vertex $v$ has been finalized.
3. `parent`: A predecessor tracking array to enable $O(L)$ route reconstruction from destination back to source.

### Greedy Selection & Edge Relaxation

At each step, the algorithm:
1. Selects an unvisited vertex $u$ with the minimum tentative distance:
   $$\min_{j \notin \text{visited}} \text{dist}[j]$$
2. Marks $u$ as visited.
3. For every neighbor $v$ connected via edge $(u, v)$ with weight $w$:
   $$\text{candidate} = \text{dist}[u] + w$$
   If $\text{candidate} < \text{dist}[v]$, the algorithm relaxes the edge:
   $$\text{dist}[v] \leftarrow \text{candidate}$$
   $$\text{parent}[v] \leftarrow u$$

---

## Lateralus Implementation

Here is the implementation in Lateralus:

```lateralus
fn dijkstra(n: int, adj: dict, source: int) -> dict {
    let INF = 1000000000;
    let mut dist = [];
    let mut visited = [];
    let mut parent = [];
    let mut i = 0;
    while i < n {
        dist = dist + [INF];
        visited = visited + [false];
        parent = parent + [-1];
        i = i + 1;
    }

    dist[source] = 0;

    let mut step = 0;
    while step < n {
        let mut u = -1;
        let mut min_d = INF;
        let mut j = 0;
        while j < n {
            if visited[j] == false && dist[j] < min_d {
                min_d = dist[j];
                u = j;
            }
            j = j + 1;
        }

        if u == -1 {
            step = n; // All remaining vertices are unreachable
        } else {
            visited[u] = true;
            if contains(adj, u) {
                let neighbors = adj[u];
                let mut k = 0;
                while k < len(neighbors) {
                    let edge = neighbors[k];
                    let v = edge[0];
                    let weight = edge[1];
                    if visited[v] == false {
                        let candidate = dist[u] + weight;
                        if candidate < dist[v] {
                            dist[v] = candidate;
                            parent[v] = u;
                        }
                    }
                    k = k + 1;
                }
            }
            step = step + 1;
        }
    }

    let mut result = {};
    result["dist"] = dist;
    result["parent"] = parent;
    return result;
}

fn reconstruct_path(parent: list, target: int) -> list {
    let mut path = [];
    let mut curr = target;
    while curr != -1 {
        path = [curr] + path;
        curr = parent[curr];
    }
    return path;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_dijkstra_tutorial.ltl` tests key properties:

1. **5-Node Weighted Topology**:
   - `0 -> (1, 4), (2, 2)`
   - `1 -> (2, 1), (3, 5)`
   - `2 -> (3, 8), (4, 10)`
   - `3 -> (4, 2)`
   - Verifies relaxation selecting path $0 \to 1 \to 3 \to 4$ (cost 11) over $0 \to 2 \to 4$ (cost 12).
2. **Path Reconstruction**:
   - `reconstruct_path(parent, 4)` reproduces `[0, 1, 3, 4]`.
3. **Unreachable Disconnected Subgraphs**:
   - Verifies disconnected vertices remain with distance `INF` and `parent = -1`.
4. **Single-Node Base Case**:
   - Verifies $n=1$, distance to source is `0`, parent is `-1`.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_dijkstra_tutorial.ltl
python -m lateralus_lang check examples/dijkstra_tutorial.ltl
pytest tests/test_compiler.py
```
