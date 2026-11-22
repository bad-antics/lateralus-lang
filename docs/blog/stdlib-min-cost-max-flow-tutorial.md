# Min-Cost Max-Flow & Successive Shortest Path in Lateralus

## 1. Introduction & Executive Summary

In network optimization, finding the maximum throughput between a source $s$ and sink $t$ (the classical Maximum Flow problem) is often only half the objective. In modern telecommunications, logistics, and cloud infrastructure, transmitting data or goods across physical edges incurs economic costs. 

The **Minimum-Cost Maximum-Flow (MCMF)** problem seeks to route the maximum possible flow from $s$ to $t$ through a directed capacitated network while minimizing the total cost $\sum_{e} f(e) \cdot \text{cost}(e)$.

Rooted in the seminal **Successive Shortest Path (SSP)** paradigm formulated by **Busacker and Gowen (1961)** and formalized by **Jack Edmonds and Richard M. Karp (1972)**, MCMF iteratively augments flow along the cheapest path in the residual graph. Paired with **Morton Klein's (1967) negative-cycle optimality theorem**, this approach mathematically guarantees that the final saturated flow achieves global minimal expenditure.

This tutorial provides complete mathematical proofs of residual skew-symmetry and delivers a verified production implementation in Lateralus.

---

## 2. Mathematical Foundations & Optimality Invariants

Let $G = (V, E)$ be a directed graph with source $s$, sink $t$, capacities $u(e) \in \mathbb{R}^+$, and per-unit costs $c(e) \in \mathbb{R}$.

### 2.1 The Residual Network & Skew-Symmetry
For any flow function $f: E \to \mathbb{R}^+$, the **Residual Network** $G_f = (V, E_f)$ contains:
1. **Forward Edges**: If $f(u, v) < u(u, v)$, edge $(u, v)$ has residual capacity $r(u, v) = u(u, v) - f(u, v)$ and cost $c(u, v)$.
2. **Reverse Edges**: If $f(u, v) > 0$, reverse edge $(v, u)$ has residual capacity $r(v, u) = f(u, v)$ and cost:
   $$c(v, u) = -c(u, v)$$

This skew-symmetry ensures that pushing flow along a reverse edge $(v, u)$ cancels previously allocated forward flow along $(u, v)$, refunding $c(u, v)$ per unit.

---

### 2.2 Theorem (Klein 1967: Negative-Cycle Optimality)
*A flow $f$ has minimum cost among all flows of value $|f|$ if and only if the residual network $G_f$ contains no negative-cost directed cycles.*

#### Proof:
1. **$(\Rightarrow)$**: Suppose $G_f$ contains a directed cycle $\Gamma$ with $\text{cost}(\Gamma) = \sum_{e \in \Gamma} c(e) < 0$. Pushing $\epsilon = \min_{e \in \Gamma} r(e) > 0$ units of flow along $\Gamma$ does not change the net flow value $|f|$ entering $t$, but alters total cost by $\epsilon \cdot \text{cost}(\Gamma) < 0$, contradicting the minimality of $f$.
2. **$(\Leftarrow)$**: Suppose $f'$ is another flow with $|f'| = |f|$ and $\text{cost}(f') < \text{cost}(f)$. Consider the difference flow $f' - f$. By flow conservation, $f' - f$ decomposes into a collection of directed cycles in $G_f$. If none of these cycles had negative cost, then $\text{cost}(f' - f) \ge 0 \implies \text{cost}(f') \ge \text{cost}(f)$, yielding a contradiction. $\blacksquare$

---

### 2.3 The Successive Shortest Path (SSP) Invariant
The algorithm begins with zero flow $f \equiv 0$. The initial residual network $G_0$ contains only forward edges; assuming no negative cycles exist initially, $G_0$ satisfies Klein's invariant.

In each iteration, SSP finds the shortest path $P$ from $s$ to $t$ in $G_f$ with respect to cost $c$. Augmenting along $P$ by bottleneck capacity $\delta = \min_{e \in P} r(e)$ produces a new flow $f'$ whose residual graph $G_{f'}$ remains free of negative cycles.

---

## 3. Algorithmic Mechanics: SPFA Augmentation

Because reverse edges carry negative costs $-c(e)$, standard Dijkstra cannot be directly applied without node potentials. Instead, we employ the **Shortest Path Faster Algorithm (SPFA)**—a FIFO queue-optimized relaxation of Bellman-Ford:

1. Maintain `dist[u]` representing the minimum cost from $s$ to $u$.
2. Push $s$ into a relaxation queue. While the queue is non-empty, pop $u$ and relax all outbound edges $(u, v)$ with $r(u, v) > 0$.
3. When $t$ is unreachable, the algorithm terminates; the maximum flow and minimum total cost have been attained.

---

## 4. Lateralus Implementation

```lateralus
// stdlib/min_cost_max_flow.ltl
pub fn mcmf_create(n: int) -> dict {
    let mut net = {}
    net["n"] = n

    let mut head = []
    let mut i = 0
    while i <= n {
        head.push([])
        i = i + 1
    }

    net["head"] = head
    net["edge_to"] = []
    net["edge_cap"] = []
    net["edge_cost"] = []
    return net
}

pub fn mcmf_add_edge(net: dict, u: int, v: int, cap: int, cost: int) {
    let mut head = net["head"]
    let mut edge_to = net["edge_to"]
    let mut edge_cap = net["edge_cap"]
    let mut edge_cost = net["edge_cost"]

    let forward_id = edge_to.len()
    let reverse_id = forward_id + 1

    edge_to.push(v)
    edge_cap.push(cap)
    edge_cost.push(cost)

    let mut u_edges = head[u]
    u_edges.push(forward_id)
    head[u] = u_edges

    edge_to.push(u)
    edge_cap.push(0)
    edge_cost.push(0 - cost)

    let mut v_edges = head[v]
    v_edges.push(reverse_id)
    head[v] = v_edges
}

pub fn mcmf_solve(net: dict, s: int, t: int) -> dict {
    let n = net["n"]
    let head = net["head"]
    let edge_to = net["edge_to"]
    let mut edge_cap = net["edge_cap"]
    let edge_cost = net["edge_cost"]

    let inf_cost = 1000000000
    let mut total_flow = 0
    let mut total_cost = 0

    let mut has_path = true
    while has_path {
        let mut dist = []
        let mut parent_edge = []
        let mut in_queue = []

        let mut i = 0
        while i <= n {
            dist.push(inf_cost)
            parent_edge.push(-1)
            in_queue.push(false)
            i = i + 1
        }

        dist[s] = 0
        let mut queue = [s]
        in_queue[s] = true
        let mut q_head = 0

        while q_head < queue.len() {
            let u = queue[q_head]
            q_head = q_head + 1
            in_queue[u] = false

            let u_edges = head[u]
            let n_edges = u_edges.len()
            let mut j = 0
            while j < n_edges {
                let e = u_edges[j]
                let v = edge_to[e]
                let cap = edge_cap[e]
                let c = edge_cost[e]

                if cap > 0 and dist[u] + c < dist[v] {
                    dist[v] = dist[u] + c
                    parent_edge[v] = e
                    if not in_queue[v] {
                        queue.push(v)
                        in_queue[v] = true
                    }
                }
                j = j + 1
            }
        }

        if dist[t] >= inf_cost {
            has_path = false
        } else {
            let mut bottleneck = 1000000000
            let mut curr = t
            while curr != s {
                let e = parent_edge[curr]
                let cap = edge_cap[e]
                if cap < bottleneck {
                    bottleneck = cap
                }
                if e % 2 == 0 {
                    curr = edge_to[e + 1]
                } else {
                    curr = edge_to[e - 1]
                }
            }

            curr = t
            while curr != s {
                let e = parent_edge[curr]
                let next_node = 0
                if e % 2 == 0 {
                    next_node = edge_to[e + 1]
                    edge_cap[e] = edge_cap[e] - bottleneck
                    edge_cap[e + 1] = edge_cap[e + 1] + bottleneck
                } else {
                    next_node = edge_to[e - 1]
                    edge_cap[e] = edge_cap[e] - bottleneck
                    edge_cap[e - 1] = edge_cap[e - 1] + bottleneck
                }
                curr = next_node
            }

            total_flow = total_flow + bottleneck
            total_cost = total_cost + bottleneck * dist[t]
        }
    }

    let mut res = {}
    res["flow"] = total_flow
    res["cost"] = total_cost
    return res
}
```

---

## 5. Complexity & Performance Metrics

| Operation | Complexity | Description |
| :--- | :--- | :--- |
| **SPFA Augmenting Phase** | $O(|V| \cdot |E|)$ worst-case | Finding cheapest path with negative edges |
| **Total Solve Time** | $O(|F| \cdot |V| \cdot |E|)$ | Where $|F|$ is total maximum flow |
| **Residual Space** | $O(|V| + |E|)$ | Flat arrays for forward and reverse edges |

---

## 6. Real-World Case Study: Cloud Bandwidth Egress Routing

In multi-region cloud applications, outbound traffic from primary compute zones to central analytics storage can travel over direct or peered WAN links:

```lateralus
fn main() {
    let net = mcmf_create(5)
    mcmf_add_edge(net, 1, 2, 40, 2)  // 40 Gbps @ $2/Gbps
    mcmf_add_edge(net, 1, 3, 30, 4)  // 30 Gbps @ $4/Gbps
    mcmf_add_edge(net, 2, 4, 25, 1)  // 25 Gbps @ $1/Gbps
    mcmf_add_edge(net, 3, 4, 30, 2)  // 30 Gbps @ $2/Gbps
    mcmf_add_edge(net, 2, 5, 20, 5)  // 20 Gbps direct @ $5/Gbps
    mcmf_add_edge(net, 4, 5, 50, 1)  // 50 Gbps @ $1/Gbps

    let solution = mcmf_solve(net, 1, 5)
    print("Maximum Routed Bandwidth (Gbps): ")
    print(solution["flow"])
    print("Optimal Total Egress Cost ($): ")
    print(solution["cost"])
}
```

The algorithm systematically routes across the lowest-cost paths first, achieving maximum network throughput with mathematically proven minimal expenditure.

---

## 7. Conclusion

Min-Cost Max-Flow unites combinatorial graph search with linear optimization. Through residual skew-symmetry and successive shortest path augmentation, it delivers optimal flow distributions across computational networks, transportation logistics, and cloud infrastructure.
