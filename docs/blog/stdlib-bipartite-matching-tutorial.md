# Maximum Bipartite Matching in Lateralus

## 1. Introduction

A graph $G = (V, E)$ is **bipartite** if its vertex set can be partitioned into two disjoint subsets $U$ and $W$ ($V = U \cup W, U \cap W = \emptyset$) such that every edge in $E$ connects a vertex in $U$ to a vertex in $W$.

A **Matching** $M \subseteq E$ is a set of pairwise non-adjacent edges—no two edges share a common endpoint. A **Maximum Bipartite Matching** is a matching that achieves the maximum possible cardinality:

$$\max |M|$$

Matching theory forms the bedrock of combinatorial optimization, market clearance mechanisms, and operations research. It underpins:
- **Decentralized Finance (DeFi) Order Crossing**: Matching buy and sell limit orders without centralized counterparty risk.
- **Task Dispatch & Cloud Scheduling**: Pairing computing jobs to available heterogeneous cluster worker nodes.
- **Ride-Sharing Logistics**: Pairing passengers to nearby drivers to maximize total trip fulfillment.

This tutorial provides a complete walkthrough of implementing the Maximum Bipartite Matching algorithm via augmenting paths in Lateralus (`stdlib/bipartite_matching.ltl`), complete with decentralized order book clearing and golden test vectors.

---

## 2. Theoretical Guarantees & Theorems

### 2.1 Berge's Lemma & Augmenting Paths
Given a matching $M$:
- A path $P$ is an **alternating path** if its edges alternate between non-matching edges ($E \setminus M$) and matching edges ($M$).
- An **augmenting path** is an alternating path that begins and ends at *unmatched* vertices.

> **Berge's Lemma (1957)**: A matching $M$ is maximum if and only if there exists no augmenting path with respect to $M$.

Whenever an augmenting path $P$ is discovered, taking the symmetric difference:

$$M' = M \oplus P = (M \setminus P) \cup (P \setminus M)$$

swaps the status of all edges along $P$. Because $P$ starts and ends with unmatched edges, $P$ contains exactly one more non-matching edge than matching edge, increasing $|M|$ by $+1$!

### 2.2 König's Duality Theorem
A **Vertex Cover** is a subset of vertices that touches every edge in the graph.
> **König's Theorem (1931)**: In any bipartite graph, the maximum cardinality of a matching equals the minimum cardinality of a vertex cover:
>
> $$\max |M| = \min |C|$$

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
fn init_adj(n) {
    let adj = dict()
    let i = 0
    while i < n {
        adj[i] = []
        i = i + 1
    }
    return adj
}

fn add_bipartite_edge(adj, u, v) {
    adj[u] = push(adj[u], v)
}

fn dfs_augment(u, adj, match_r, visited) {
    let neighbors = adj[u]
    let i = 0
    while i < len(neighbors) {
        let v = neighbors[i]
        if not visited[v] {
            visited[v] = true
            if match_r[v] == -1 or dfs_augment(match_r[v], adj, match_r, visited) {
                match_r[v] = u
                return true
            }
        }
        i = i + 1
    }
    return false
}

pub fn max_bipartite_matching(n1, n2, adj) {
    let match_r = dict()
    let j = 0
    while j < n2 {
        match_r[j] = -1
        j = j + 1
    }

    let match_count = 0
    let u = 0
    while u < n1 {
        let visited = dict()
        let k = 0
        while k < n2 {
            visited[k] = false
            k = k + 1
        }

        if dfs_augment(u, adj, match_r, visited) {
            match_count = match_count + 1
        }
        u = u + 1
    }

    let match_l = dict()
    let l_idx = 0
    while l_idx < n1 {
        match_l[l_idx] = -1
        l_idx = l_idx + 1
    }

    let r_idx = 0
    while r_idx < n2 {
        let matched_u = match_r[r_idx]
        if matched_u != -1 {
            match_l[matched_u] = r_idx
        }
        r_idx = r_idx + 1
    }

    let res = dict()
    res["matching_size"] = match_count
    res["match_l"] = match_l
    res["match_r"] = match_r
    return res
}
```

---

## 4. Real-World Engineering Applications

1. **Decentralized Limit Order Book Crossing**: Matching maker liquidity with taker demand across non-fungible or batch token markets.
2. **Kubernetes Pod-to-Node Scheduling**: Mapping compute workloads to cluster worker nodes respecting affinity and resource constraints.
3. **Ride-Sharing Platform Dispatch**: Matching drivers with pending passenger ride requests in geographic sub-regions.
4. **Course Allocation & University Admissions**: Gale-Shapley matching foundations for fair multi-agent resource allocation.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_bipartite_matching_tutorial.ltl
python -m lateralus_lang check examples/bipartite_matching_tutorial.ltl
pytest tests/test_compiler.py
```
