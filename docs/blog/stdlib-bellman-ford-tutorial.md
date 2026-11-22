# Bellman-Ford Tutorial: Negative Edge Relaxation and Arbitrage Cycle Detection

## Overview

While Dijkstra's algorithm efficiently computes single-source shortest paths on graphs with non-negative edge weights, it fails in the presence of negative edge weights. The **Bellman-Ford algorithm** (conceived by Alfonso Shimbel, Richard Bellman, and Lester Ford Jr.) resolves this by systematically relaxing all edges $|V| - 1$ times. Furthermore, it reliably detects **negative-weight cycles**.

In modern decentralized finance (DeFi) and crypto algorithmic trading, Bellman-Ford is heavily employed for **triangular and cross-exchange arbitrage detection**:
- When currency exchange rates are mapped via logarithmic transforms:
  $$\text{weight}(A \to B) = -\ln(\text{rate}(A \to B))$$
- A profitable cycle where the product of exchange rates exceeds 1 translates directly into a directed cycle with a negative sum of weights:
  $$\sum -\ln(\text{rate}) < 0$$

---

## Algorithm Mechanics

Given a graph $G = (V, E)$ with $|V| = n$:

1. **Initialization**: Set $\text{dist}[\text{source}] = 0$ and all other distances to $\infty$.
2. **Relaxation Passes**:
   - Execute $|V| - 1$ iterations. In each iteration, iterate over all edges $(u, v) \in E$:
     $$\text{if } \text{dist}[u] \neq \infty \text{ and } \text{dist}[u] + w(u, v) < \text{dist}[v]:$$
     $$\text{dist}[v] \leftarrow \text{dist}[u] + w(u, v)$$
     $$\text{parent}[v] \leftarrow u$$
   - *Convergence Optimization*: If no distance updates occur during an iteration, the algorithm terminates early.
3. **Negative Cycle Check**:
   - Perform an $n$-th check across all edges $(u, v) \in E$.
   - If any edge can still be relaxed ($\text{dist}[u] + w(u, v) < \text{dist}[v]$), a negative-weight cycle exists reachable from the source.

Time complexity is $O(|V| \cdot |E|)$, with $O(|V|)$ auxiliary space.

---

## Lateralus Implementation

```lateralus
fn bellman_ford(n: int, edges: list, source: int) -> dict {
    let INF = 1000000000;
    let mut dist = [];
    let mut parent = [];
    let mut i = 0;
    while i < n {
        dist = dist + [INF];
        parent = parent + [-1];
        i = i + 1;
    }
    dist[source] = 0;

    let mut iter = 0;
    while iter < (n - 1) {
        let mut updated = false;
        let mut e_idx = 0;
        while e_idx < len(edges) {
            let e = edges[e_idx];
            let u = e[0];
            let v = e[1];
            let w = e[2];
            if dist[u] != INF {
                if dist[u] + w < dist[v] {
                    dist[v] = dist[u] + w;
                    parent[v] = u;
                    updated = true;
                }
            }
            e_idx = e_idx + 1;
        }
        if updated == false {
            iter = n;
        } else {
            iter = iter + 1;
        }
    }

    let mut has_negative_cycle = false;
    let mut cycle_node = -1;
    let mut k = 0;
    while k < len(edges) {
        let e2 = edges[k];
        let u2 = e2[0];
        let v2 = e2[1];
        let w2 = e2[2];
        if dist[u2] != INF {
            if dist[u2] + w2 < dist[v2] {
                has_negative_cycle = true;
                cycle_node = v2;
                k = len(edges);
            }
        }
        k = k + 1;
    }

    let mut result = {};
    result["dist"] = dist;
    result["parent"] = parent;
    result["has_negative_cycle"] = has_negative_cycle;
    result["cycle_node"] = cycle_node;
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

The test suite in `tests/stdlib_bellman_ford_tutorial.ltl` validates:

1. **Negative Weights Without Negative Cycle**:
   - Computes correct minimum path $0 \to 2 \to 3 \to 1 \to 4$ with total negative cost $-2$.
   - Verifies route reconstruction reproducing exact vertex sequence `[0, 2, 3, 1, 4]`.
2. **Negative Cycle Detection (Arbitrage Loop)**:
   - Cycle $1 \to 2 \to 3 \to 1$ with sum $2 + 3 + (-6) = -1 < 0$ correctly triggers `has_negative_cycle = true`.
3. **Unreachable Vertices**:
   - Verifies disconnected vertices remain safely bound at `INF`.
4. **Single-node Base Case**:
   - Verifies zero-edge graph terminates with distance 0.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_bellman_ford_tutorial.ltl
python -m lateralus_lang check examples/bellman_ford_tutorial.ltl
pytest tests/test_compiler.py
```
