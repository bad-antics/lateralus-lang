# Floyd-Warshall Tutorial: All-Pairs Shortest Paths and Dynamic Programming

## Overview

The **Floyd-Warshall algorithm** (independently developed by Bernard Roy, Robert Floyd, and Stephen Warshall) is a classic dynamic programming algorithm that finds shortest paths between all pairs of vertices in a directed, weighted graph with positive or negative edge weights (provided no negative-weight cycles exist).

Alongside Dijkstra (Single-Source Shortest Path with non-negative weights, $O(|E| + |V| \log |V|)$) and Bellman-Ford (Single-Source Shortest Path with arbitrary weights, $O(|V| \cdot |E|)$), Floyd-Warshall completes the foundational shortest path triumvirate by computing all-pairs shortest paths in $O(|V|^3)$ time.

In distributed cloud networks and routing topologies, Floyd-Warshall is used for:
- **Global Network Routing Matrices**: Computing all-pairs inter-region ping latencies for optimal cloud CDN traffic steering.
- **Transitive Closure**: Evaluating reachability between any pair of nodes in directed graphs (Warshall's boolean variant).
- **Arbitrage and Negative Cycle Detection**: Verifying whether diagonal elements $\text{dist}[i][i] < 0$ after $n$ phases.

---

## Dynamic Programming Recurrence

Let vertices be indexed from $0$ to $n-1$.

Define $D^{(k)}[i][j]$ as the shortest path from vertex $i$ to vertex $j$ using only intermediate vertices from the prefix set $\{0, 1, \dots, k\}$.

### Recurrence Relation

For phase $k \in [0, n-1]$:
$$D^{(k)}[i][j] = \min \left( D^{(k-1)}[i][j], D^{(k-1)}[i][k] + D^{(k-1)}[k][j] \right)$$

Because $D^{(k)}[i][k] = D^{(k-1)}[i][k]$ and $D^{(k)}[k][j] = D^{(k-1)}[k][j]$, the third dimension $k$ can be reduced entirely in-place to a single 2D $n \times n$ matrix:
$$\text{dist}[i][j] \leftarrow \min(\text{dist}[i][j], \text{dist}[i][k] + \text{dist}[k][j])$$

### Negative-Weight Cycle Detection

In a graph without negative cycles, the shortest distance from any node $i$ to itself is strictly 0. If after $n$ iterations any diagonal element $\text{dist}[i][i] < 0$, a negative-weight cycle is reachable.

Time complexity is $O(|V|^3)$ with $O(|V|^2)$ auxiliary space.

---

## Lateralus Implementation

```lateralus
fn floyd_warshall(n: int, edges: list) -> dict {
    let INF = 1000000000;
    let mut dist = [];
    let mut i = 0;
    while i < n {
        let mut row = [];
        let mut j = 0;
        while j < n {
            if i == j {
                row = row + [0];
            } else {
                row = row + [INF];
            }
            j = j + 1;
        }
        dist = dist + [row];
        i = i + 1;
    }

    let mut e_idx = 0;
    while e_idx < len(edges) {
        let e = edges[e_idx];
        let u = e[0];
        let v = e[1];
        let w = e[2];
        if w < dist[u][v] {
            dist[u][v] = w;
        }
        e_idx = e_idx + 1;
    }

    let mut k = 0;
    while k < n {
        let mut r = 0;
        while r < n {
            let mut c = 0;
            while c < n {
                if dist[r][k] != INF && dist[k][c] != INF {
                    let cand = dist[r][k] + dist[k][c];
                    if cand < dist[r][c] {
                        dist[r][c] = cand;
                    }
                }
                c = c + 1;
            }
            r = r + 1;
        }
        k = k + 1;
    }

    let mut has_negative_cycle = false;
    let mut diag = 0;
    while diag < n {
        if dist[diag][diag] < 0 {
            has_negative_cycle = true;
            diag = n;
        } else {
            diag = diag + 1;
        }
    }

    let mut result = {};
    result["dist"] = dist;
    result["has_negative_cycle"] = has_negative_cycle;
    return result;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_floyd_warshall_tutorial.ltl` validates:

1. **4-Node Network Intermediate Optimization**:
   - Optimal path $0 \to 3$ via intermediate nodes $0 \to 1 \to 2 \to 3$ with cost 9 (beating direct edge 10).
2. **Negative Edge Accommodation**:
   - Negative weight edge successfully improves distance ($0 \to 2 \to 1$ cost $-1$).
3. **Negative-Weight Cycle Detection**:
   - Directed cycle with negative sum ($0 \to 1 \to 2 \to 0$, sum $-2$) successfully triggers `has_negative_cycle = true`.
4. **Single-Node Base Case**:
   - Self-loop distance remains 0.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_floyd_warshall_tutorial.ltl
python -m lateralus_lang check examples/floyd_warshall_tutorial.ltl
pytest tests/test_compiler.py
```
