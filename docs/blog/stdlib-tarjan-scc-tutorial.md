# Tarjan's Strongly Connected Components (SCC) Algorithm in Lateralus

## 1. Introduction

In directed graph theory, a directed graph is **strongly connected** if every vertex is reachable from every other vertex. For an arbitrary directed graph $G = (V, E)$, the graph can be uniquely partitioned into maximal strongly connected subgraphs, known as **Strongly Connected Components (SCCs)**.

Discovered by Robert E. Tarjan in 1972, **Tarjan's SCC Algorithm** partitions any directed graph into its strongly connected components in strict linear time:

$$\mathcal{O}(|V| + |E|)$$

Unlike Kosaraju's two-pass algorithm (which requires constructing the transposed graph $G^T$), Tarjan's algorithm achieves complete component decomposition in a **single depth-first search (DFS) traversal** by cleverly leveraging an explicit recursion stack and low-link numbers.

This tutorial provides a complete walkthrough of implementing Tarjan's SCC algorithm in Lateralus (`stdlib/tarjan_scc.ltl`), along with golden test vectors and real-world microservice dependency analysis.

---

## 2. Core Theoretical Mechanics

### 2.1 DFS Tree Edges Classification
During a depth-first traversal of a directed graph, edges fall into four distinct categories:
1. **Tree Edges**: Edges leading to previously unvisited vertices in the DFS forest.
2. **Back Edges**: Edges leading to an ancestor in the active DFS path, forming directed cycles.
3. **Forward Edges**: Edges leading to a descendant already visited in the DFS subtree.
4. **Cross Edges**: Edges connecting two vertices that are neither ancestors nor descendants of each other.

### 2.2 Invariants: `dfn` and `low`
For each vertex $u$, Tarjan's algorithm tracks two key integer timestamps:
- **`dfn[u]` (Discovery Time)**: The order in which vertex $u$ was first visited during DFS traversal.
- **`low[u]` (Lowest Reachable Link)**: The smallest `dfn` value reachable from $u$ through its DFS subtree and at most one back-edge or cross-edge pointing to an active vertex on the recursion stack.

$$\text{low}[u] = \min \begin{cases}
\text{dfn}[u] \\
\text{low}[v] & \text{if } (u, v) \text{ is a tree edge} \\
\text{dfn}[v] & \text{if } (u, v) \text{ is a back/cross edge and } v \in \text{Stack}
\end{cases}$$

### 2.3 SCC Root Condition
A vertex $u$ is the **root** of an SCC if and only if:

$$\text{low}[u] == \text{dfn}[u]$$

When this condition is met upon returning from all outgoing DFS branches:
1. Every vertex pushed onto the stack after $u$ belongs to the same SCC.
2. We repeatedly pop elements from the stack until $u$ itself is popped.
3. All popped vertices form one complete, maximal strongly connected component!

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
fn min_val(a, b) {
    if a < b {
        return a
    }
    return b
}

fn tarjan_dfs(u, adj, state) {
    state["timer"] = state["timer"] + 1
    state["dfn"][u] = state["timer"]
    state["low"][u] = state["timer"]
    state["stack"] = push(state["stack"], u)
    state["in_stack"][u] = true

    let neighbors = adj[u]
    let i = 0
    while i < len(neighbors) {
        let v = neighbors[i]
        if state["dfn"][v] == 0 {
            tarjan_dfs(v, adj, state)
            state["low"][u] = min_val(state["low"][u], state["low"][v])
        } else {
            if state["in_stack"][v] {
                state["low"][u] = min_val(state["low"][u], state["dfn"][v])
            }
        }
        i = i + 1
    }

    if state["low"][u] == state["dfn"][u] {
        let comp = []
        let done = false
        while not done {
            let top_idx = len(state["stack"]) - 1
            let w = state["stack"][top_idx]
            state["stack"] = slice(state["stack"], 0, top_idx)
            state["in_stack"][w] = false
            comp = push(comp, w)
            if w == u {
                done = true
            }
        }
        state["sccs"] = push(state["sccs"], comp)
    }
}

pub fn tarjan_scc(n, adj) {
    let state = dict()
    state["dfn"] = dict()
    state["low"] = dict()
    state["in_stack"] = dict()
    state["stack"] = []
    state["sccs"] = []
    state["timer"] = 0

    let i = 0
    while i < n {
        state["dfn"][i] = 0
        state["low"][i] = 0
        state["in_stack"][i] = false
        i = i + 1
    }

    let u = 0
    while u < n {
        if state["dfn"][u] == 0 {
            tarjan_dfs(u, adj, state)
        }
        u = u + 1
    }

    return state["sccs"]
}
```

---

## 4. Real-World Applications

1. **Compiler Optimization & Deadlock Detection**: Condensing SCCs allows compilers to identify mutually recursive functions and build safe topological evaluation orders.
2. **Package Dependency Resolution**: Identifies circular import cycles (`A -> B -> C -> A`) in build systems like Cargo, npm, or Bazel.
3. **Database Concurrency Control**: Detects deadlocks in distributed wait-for graphs (WFGs).

---

## 5. Verification & Testing

Run verification via the Lateralus CLI:

```bash
python -m lateralus_lang check tests/stdlib_tarjan_scc_tutorial.ltl
python -m lateralus_lang check examples/tarjan_scc_tutorial.ltl
pytest tests/test_compiler.py
```
