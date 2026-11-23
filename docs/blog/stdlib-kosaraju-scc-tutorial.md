# Kosaraju-Sharir Strongly Connected Components (SCC) Algorithm in Lateralus

## 1. Introduction

In a directed graph $G = (V, E)$, a **Strongly Connected Component (SCC)** is a maximal subset of vertices $U \subseteq V$ such that every vertex in $U$ is reachable from every other vertex in $U$.

While **Tarjan's Algorithm** decomposes SCCs in a single pass using integer low-link timestamps and an explicit recursion stack, the **Kosaraju-Sharir Algorithm** (discovered by S. Rao Kosaraju in 1978 and independently by Micha Sharir in 1981) provides a conceptually elegant, two-pass depth-first search (DFS) method based on the properties of the **transposed graph** $G^T$.

Both algorithms operate in optimal linear time:

$$\mathcal{O}(|V| + |E|)$$

Kosaraju's algorithm is especially favored in distributed big-data graph processing and map-reduce engines because the transposed graph $G^T$ can be generated via simple edge inversion without maintaining fine-grained timestamp updates.

This tutorial presents an implementation of the Kosaraju-Sharir algorithm in Lateralus (`stdlib/kosaraju_scc.ltl`), complete with social network mutual community discovery and golden test vectors.

---

## 2. Mathematical Duality & The Two-Pass Mechanism

### 2.1 The Transposed Graph $G^T$
For any directed graph $G = (V, E)$, its **transposed graph** $G^T = (V, E^T)$ possesses the identical vertex set, with all directed edge orientations reversed:

$$(u, v) \in E \iff (v, u) \in E^T$$

**Key Mathematical Invariant**:
> $u$ and $v$ belong to the same SCC in $G$ if and only if they belong to the same SCC in $G^T$.

However, while individual SCCs remain internally unchanged, the edges *between* different SCCs in the contracted component Directed Acyclic Graph (DAG) are entirely inverted!

### 2.2 Why the Two-Pass Strategy Works
1. **Pass 1 (Finishing Time Stack)**:
   Run standard DFS on $G$. When a vertex finishes all outgoing explorations, push it onto a LIFO stack. The top of the stack will be guaranteed to contain a vertex belonging to a "source" component in the component DAG.
2. **Pass 2 (Transposed Traversal)**:
   Pop vertices from the stack in decreasing order of finishing time. On the transposed graph $G^T$, any "source" component becomes a "sink" component.
   Consequently, starting a DFS from the popped vertex on $G^T$ traverses *only* the vertices within its own SCC—it cannot escape to other components because the transposed inter-component edges point strictly inward!

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

fn add_edge(adj, u, v) {
    adj[u] = push(adj[u], v)
}

fn dfs1(u, adj, visited, order_ref) {
    visited[u] = true
    let neighbors = adj[u]
    let i = 0
    while i < len(neighbors) {
        let v = neighbors[i]
        if not visited[v] {
            dfs1(v, adj, visited, order_ref)
        }
        i = i + 1
    }
    order_ref["stack"] = push(order_ref["stack"], u)
}

fn dfs2(u, rev_adj, visited, comp_ref) {
    visited[u] = true
    comp_ref["nodes"] = push(comp_ref["nodes"], u)
    let neighbors = rev_adj[u]
    let i = 0
    while i < len(neighbors) {
        let v = neighbors[i]
        if not visited[v] {
            dfs2(v, rev_adj, visited, comp_ref)
        }
        i = i + 1
    }
}

pub fn kosaraju_scc(n, adj) {
    let visited1 = dict()
    let i = 0
    while i < n {
        visited1[i] = false
        i = i + 1
    }

    let order_ref = dict()
    order_ref["stack"] = []

    let u = 0
    while u < n {
        if not visited1[u] {
            dfs1(u, adj, visited1, order_ref)
        }
        u = u + 1
    }

    // Build transposed graph G^T
    let rev_adj = init_adj(n)
    let src = 0
    while src < n {
        let neighbors = adj[src]
        let j = 0
        while j < len(neighbors) {
            let dst = neighbors[j]
            rev_adj[dst] = push(rev_adj[dst], src)
            j = j + 1
        }
        src = src + 1
    }

    let visited2 = dict()
    let k = 0
    while k < n {
        visited2[k] = false
        k = k + 1
    }

    let sccs = []
    let stack_idx = len(order_ref["stack"]) - 1
    while stack_idx >= 0 {
        let node = order_ref["stack"][stack_idx]
        if not visited2[node] {
            let comp_ref = dict()
            comp_ref["nodes"] = []
            dfs2(node, rev_adj, visited2, comp_ref)
            sccs = push(sccs, comp_ref["nodes"])
        }
        stack_idx = stack_idx - 1
    }

    return sccs
}
```

---

## 4. Real-World Engineering Applications

1. **Social Network Community Clusters**: Detecting densely interconnected reciprocal follower rings in platforms like Twitter/X or Farcaster.
2. **Web Graph & SEO Authority Analysis**: Grouping mutually linked web pages to analyze PageRank hubs and link spam rings.
3. **2-Satisfiability (2-SAT) Problem**: Determining boolean formula satisfiability by inspecting whether variable $x$ and $\neg x$ belong to the same SCC in the implication graph.
4. **Compiler Dead-Code Elimination**: Contracting mutually recursive subroutines into single supernodes for global static code analysis.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_kosaraju_scc_tutorial.ltl
python -m lateralus_lang check examples/kosaraju_scc_tutorial.ltl
pytest tests/test_compiler.py
```
