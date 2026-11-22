# Standard Library Deep Dive: Lowest Common Ancestor (LCA) via Binary Lifting

The **Lowest Common Ancestor (LCA)** problem on rooted trees is a foundational primitive in graph theory, distributed systems, and compiler design. Given a rooted tree $T = (V, E)$ with $|V| = n$, and two arbitrary query nodes $u, v \in V$, the task is to identify the unique node $w \in V$ that is an ancestor of both $u$ and $v$ and lies at the maximum tree depth.

While naive depth-matching and parent-pointer climbing take worst-case $O(n)$ time on skewed or chain-like trees, **Binary Lifting** offers optimal amortized performance:
- **Precomputation Time & Space**: $O(n \log n)$ via a single Depth-First Search (DFS) pass.
- **Online Query Time**: Guaranteed $O(\log n)$ per LCA and tree distance evaluation.

---

## 1. Algorithmic Architecture & Dynamic Programming Formulation

### The Power-of-Two Jump Table

Let $up[i][u]$ denote the $2^i$-th ancestor of vertex $u$. By decomposing power-of-two jumps:

$$up[i][u] = up[i-1]\Big(up[i-1][u]\Big)$$

- Base case ($i = 0$): $up[0][u] = \text{parent}[u]$.
- For any node where $2^i$ exceeds its distance to the tree root, we clamp $up[i][u] = \text{root}$. This root-clamping boundary condition eliminates boundary checks during upward traversal.

```
                  Root (0)
                 /        \
              1 (2^0)      2
             /   \          \
          3 (2^1) 4          5
         /
      6 (2^2)
```

In this structure, node 6 can jump directly to 3 via $up[0][6]$, to 1 via $up[1][6]$, and to 0 via $up[2][6]$.

---

## 2. Two-Phase Query Resolution

Given two nodes $u$ and $v$:

### Phase 1: Depth Equalization
Assume without loss of generality that $\text{depth}[u] \ge \text{depth}[v]$. Compute difference:

$$\Delta = \text{depth}[u] - \text{depth}[v]$$

Represent $\Delta$ in binary. For each bit position $i$ from $\lfloor \log_2 n \rfloor$ down to $0$, if $\Delta \ge 2^i$, replace $u \leftarrow up[i][u]$ and $\Delta \leftarrow \Delta - 2^i$. After this step, $\text{depth}[u] = \text{depth}[v]$.

If $u == v$, then $v$ was an ancestor of $u$, and the query immediately returns $u$.

### Phase 2: Simultaneous Binary Climbing
When $u \ne v$, iterate $i$ from $\lfloor \log_2 n \rfloor$ down to $0$:
- If $up[i][u] \ne up[i][v]$, both nodes are strictly below their common ancestor at step $2^i$. We simultaneously jump: $u \leftarrow up[i][u]$, $v \leftarrow up[i][v]$.
- If $up[i][u] == up[i][v]$, the jump is too high (it lands on or above the LCA); we stay at the current nodes and test smaller powers.

At termination, $u$ and $v$ are immediate children of the true LCA. The answer is simply:

$$\text{LCA}(u, v) = up[0][u]$$

---

## 3. Tree Distance & Path Length Calculation

With LCA known, the unique simple path distance $\text{dist}(u, v)$ between any two nodes on an unweighted tree is computable in $O(1)$:

$$\text{dist}(u, v) = \text{depth}[u] + \text{depth}[v] - 2 \cdot \text{depth}[\text{LCA}(u, v)]$$

---

## 4. Lateralus Reference Implementation

```lateralus
fn dfs_prepare(u, p, d, adj, depth, up, log_n) {
    depth[u] = d
    up[0][u] = p

    let i = 1
    while i < log_n {
        let anc = up[i - 1][u]
        up[i][u] = up[i - 1][anc]
        i = i + 1
    }

    let nbrs = adj[u]
    let k = 0
    while k < len(nbrs) {
        let v = nbrs[k]
        if v != p {
            dfs_prepare(v, u, d + 1, adj, depth, up, log_n)
        }
        k = k + 1
    }
}

pub fn query_lca(info, u_in, v_in) {
    let depth = info["depth"]
    let up = info["up"]
    let log_n = info["log_n"]
    let pow2 = info["pow2"]

    let u = u_in
    let v = v_in

    if depth[u] < depth[v] {
        let tmp = u
        u = v
        v = tmp
    }

    let diff = depth[u] - depth[v]
    let i = log_n - 1
    while i >= 0 {
        let p2 = pow2[i]
        if diff >= p2 {
            u = up[i][u]
            diff = diff - p2
        }
        i = i - 1
    }

    if u == v {
        return u
    }

    let j = log_n - 1
    while j >= 0 {
        if up[j][u] != up[j][v] {
            u = up[j][u]
            v = up[j][v]
        }
        j = j - 1
    }

    return up[0][u]
}
```

---

## 5. Industrial Real-World Applications

1. **Distributed Version Control (`git merge-base`)**:
   In Git DAGs and commit branch trees, finding the common ancestor commit is essential to three-way merges.
2. **Microservice Dependency Cascades**:
   Tracing the earliest shared point of failure when multiple downstream services report concurrent timeouts.
3. **Role-Based Access Control (RBAC)**:
   Determining the Least Common Privilege between two organizational roles in an enterprise hierarchy.
