# Edmonds-Karp Maximum Network Flow Algorithm in Lateralus

## 1. Introduction

The **Maximum Network Flow Problem** is a cornerstone of combinatorial optimization. Given a directed flow network $G = (V, E)$ where each directed edge $(u, v)$ possesses a non-negative capacity $c(u, v)$, along with a designated **source** vertex $s$ and **sink** vertex $t$, the objective is to push the maximum possible total flow from $s$ to $t$ without violating capacity constraints or flow conservation.

While the foundational **Ford-Fulkerson method** (1956) searches for augmenting paths arbitrarily (which can exhibit exponential time or fail to terminate with irrational capacities), the **Edmonds-Karp algorithm** (1972) refines the search by strictly utilizing **Breadth-First Search (BFS)** to identify the *shortest augmenting path* in terms of the number of edges.

This BFS guarantee proves that the length of the shortest augmenting path monotonically increases throughout execution, yielding a robust polynomial upper bound:

$$\mathcal{O}(|V| \cdot |E|^2)$$

independent of the magnitude of edge capacities!

This tutorial presents an implementation of the Edmonds-Karp algorithm in Lateralus (`stdlib/edmonds_karp.ltl`), complete with DeFi liquidity multi-hop routing examples and golden test vectors.

---

## 2. Theoretical Foundations & Theorems

### 2.1 Flow Network Axioms
A valid flow $f: V \times V \to \mathbb{R}$ must satisfy three fundamental properties:
1. **Capacity Constraint**: $0 \le f(u, v) \le c(u, v)$ for all $(u, v) \in E$.
2. **Skew Symmetry**: $f(u, v) = -f(v, u)$ for all $(u, v) \in V \times V$.
3. **Flow Conservation**: For every vertex $u \in V \setminus \{s, t\}$, the net flow into $u$ equals net flow out of $u$:

$$\sum_{v \in V} f(u, v) = 0$$

### 2.2 Residual Network & Augmenting Paths
For any flow $f$, the **residual capacity** $c_f(u, v)$ is defined as:

$$c_f(u, v) = c(u, v) - f(u, v)$$

- A forward edge $(u, v)$ with residual capacity $c(u, v) - f(u, v) > 0$ permits pushing additional flow forward.
- A reverse edge $(v, u)$ with residual capacity $f(u, v) > 0$ permits "cancelling" previously pushed flow backward.

An **Augmenting Path** $P$ is a simple directed path from $s$ to $t$ in the residual graph $G_f$ where every edge has $c_f(u, v) > 0$. The maximum additional flow that can be routed along $P$ is the bottleneck capacity:

$$c_f(P) = \min_{(u, v) \in P} c_f(u, v)$$

### 2.3 The Max-Flow Min-Cut Theorem
A cut $(S, T)$ is a partition of $V$ such that $s \in S$ and $t \in T$. The capacity of a cut is $c(S, T) = \sum_{u \in S, v \in T} c(u, v)$.
> **Theorem (Ford & Fulkerson, 1956)**: The maximum value of an $s-t$ flow equals the minimum capacity of an $s-t$ cut:
>
> $$\max |f| = \min_{(S, T)} c(S, T)$$

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
fn init_matrix(n) {
    let m = dict()
    let i = 0
    while i < n {
        let row = dict()
        let j = 0
        while j < n {
            row[j] = 0
            j = j + 1
        }
        m[i] = row
        i = i + 1
    }
    return m
}

fn init_adj(n) {
    let adj = dict()
    let i = 0
    while i < n {
        adj[i] = []
        i = i + 1
    }
    return adj
}

fn add_edge(adj, capacity, u, v, cap) {
    adj[u] = push(adj[u], v)
    adj[v] = push(adj[v], u)
    capacity[u][v] = capacity[u][v] + cap
}

fn bfs(n, adj, capacity, s, t, parent) {
    let visited = dict()
    let i = 0
    while i < n {
        visited[i] = false
        parent[i] = -1
        i = i + 1
    }

    let queue = [s]
    visited[s] = true
    let q_head = 0

    while q_head < len(queue) {
        let u = queue[q_head]
        q_head = q_head + 1

        let neighbors = adj[u]
        let k = 0
        while k < len(neighbors) {
            let v = neighbors[k]
            if not visited[v] and capacity[u][v] > 0 {
                parent[v] = u
                visited[v] = true
                if v == t {
                    return true
                }
                queue = push(queue, v)
            }
            k = k + 1
        }
    }

    return visited[t]
}

pub fn edmonds_karp(n, adj, capacity, s, t) {
    let max_flow = 0
    let parent = dict()

    while bfs(n, adj, capacity, s, t, parent) {
        let path_flow = 999999999
        let curr = t
        while curr != s {
            let p = parent[curr]
            let cap = capacity[p][curr]
            if cap < path_flow {
                path_flow = cap
            }
            curr = p
        }

        curr = t
        while curr != s {
            let p = parent[curr]
            capacity[p][curr] = capacity[p][curr] - path_flow
            capacity[curr][p] = capacity[curr][p] + path_flow
            curr = p
        }

        max_flow = max_flow + path_flow
    }

    return max_flow
}
```

---

## 4. Real-World Applications

1. **Decentralized Finance (DeFi) Multi-Hop Swaps**: Aggregating liquidity across multiple decentralized Automated Market Maker (AMM) pools (Uniswap, Curve, Balancer, SushiSwap) to execute high-volume token trades with minimum slippage.
2. **Maximum Bipartite Matching**: Pairing job applicants to vacancies, students to schools, or drivers to ride requests.
3. **Network Throughput & Load Balancing**: Calculating the maximum sustained packet transfer rate through interconnected internet routers without packet drop.
4. **Disaster Relief & Supply Chain Logistics**: Distributing humanitarian aid through road and rail networks with damaged transportation links.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_edmonds_karp_tutorial.ltl
python -m lateralus_lang check examples/edmonds_karp_tutorial.ltl
pytest tests/test_compiler.py
```
