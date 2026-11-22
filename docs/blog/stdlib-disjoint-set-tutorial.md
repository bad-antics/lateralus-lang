# Disjoint Set Union (DSU) in Lateralus: Path Compression, Union-by-Rank, and Tarjan's Inverse Ackermann Bound

In computer science, tracking dynamic partitions of an $N$-element set into disjoint (non-overlapping) equivalence classes is known as the **Disjoint Set Union (DSU)** or **Union-Find** problem. First formulated by Bernard Galler and Michael Fischer in 1964, DSU is the backbone of graph spanning tree algorithms (such as Kruskal's MST), percolation theory in physics, and loop detection in computer networking (e.g., IEEE 802.1D Spanning Tree Protocol).

In 1975, Turing Award laureate Robert Tarjan proved that augmenting disjoint-set trees with **Path Compression** and **Union by Rank** achieves an astonishing amortized time complexity per operation:

$$O(\alpha(N))$$

Where $\alpha(N)$ is the **Inverse Ackermann function**. Since $\alpha(N) \le 4$ for any $N \le 10^{80}$ (exceeding the estimated number of atoms in the observable universe), DSU operations execute in **practically constant time** $O(1)$.

In this tutorial, we implement, benchmark, and mathematically verify a complete Disjoint Set Union engine in Lateralus.

---

## 1. Dual Optimizations: Rank Bounds and Path Flattening

A naive union-find tree can degenerate into a linear linked list of depth $O(N)$ when items are merged in sequential order, degrading queries to $O(N)$. Two complementary optimizations completely eliminate this issue:

### 1.1 Union by Rank (Logarithmic Height Bound)

Each root maintains an integer `rank` representing an upper bound on the height of its subtree:
- When uniting two sets with roots $r_1, r_2$:
  - If $\operatorname{rank}(r_1) < \operatorname{rank}(r_2)$, attach $r_1$ under $r_2$.
  - If $\operatorname{rank}(r_1) > \operatorname{rank}(r_2)$, attach $r_2$ under $r_1$.
  - If $\operatorname{rank}(r_1) = \operatorname{rank}(r_2)$, attach $r_2$ under $r_1$ and increment $\operatorname{rank}(r_1) \leftarrow \operatorname{rank}(r_1) + 1$.

This invariant guarantees that a tree of rank $k$ contains at least $2^k$ nodes, enforcing a strict $O(\log N)$ maximum height even without compression.

### 1.2 Path Compression (Iterative Flattening)

During the `find(i)` traversal, every visited ancestor along the path is reassigned to point directly to the tree root:

$$\operatorname{parent}[v] \leftarrow \operatorname{root} \quad \forall v \in \operatorname{path}(i \to \operatorname{root})$$

Subsequent queries on any node along this path resolve in $O(1)$ immediate hops.

---

## 2. Invariant: Equivalence Relations & Cycle Detection

DSU maintains a valid mathematical equivalence relation ($\sim$) satisfying three core axioms:
1. **Reflexivity**: $x \sim x$ (`dsu_connected(x, x) == true`)
2. **Symmetry**: $x \sim y \iff y \sim x$
3. **Transitivity**: $x \sim y \land y \sim z \implies x \sim z$

### Cycle Detection Invariant

When processing an undirected graph edge $(u, v)$:
- If $\operatorname{find}(u) \neq \operatorname{find}(v)$, the edge connects two previously isolated subtrees. `dsu_union` merges them and decrements the component count.
- If $\operatorname{find}(u) == \operatorname{find}(v)$, the vertices are already connected through existing edges. Adding $(u, v)$ creates an **elementary graph cycle**. `dsu_union` returns `false`, preventing network loops and broadcast storms.

---

## 3. The Lateralus Implementation

### 3.1 DSU Initialization & Path Compression

```lateralus
fn dsu_make(n: int) -> dict {
    let mut parent = [];
    let mut rank = [];
    let mut i = 0;
    while i < n {
        parent = parent + [i];
        rank = rank + [0];
        i = i + 1;
    }
    let mut dsu = {};
    dsu["parent"] = parent;
    dsu["rank"] = rank;
    dsu["count"] = n;
    return dsu;
}

fn dsu_find(dsu: dict, i: int) -> int {
    let parent = dsu["parent"];
    let mut root = i;
    while root != parent[root] {
        root = parent[root];
    }
    let mut curr = i;
    while curr != root {
        let nxt = parent[curr];
        parent[curr] = root;
        curr = nxt;
    }
    return root;
}
```

### 3.2 Union by Rank with Cycle Detection

```lateralus
fn dsu_union(dsu: dict, x: int, y: int) -> bool {
    let root_x = dsu_find(dsu, x);
    let root_y = dsu_find(dsu, y);
    if root_x == root_y {
        return false; // Cycle detected: already in the same set
    }

    let rank = dsu["rank"];
    let parent = dsu["parent"];

    if rank[root_x] < rank[root_y] {
        parent[root_x] = root_y;
    } else if rank[root_x] > rank[root_y] {
        parent[root_y] = root_x;
    } else {
        parent[root_y] = root_x;
        rank[root_x] = rank[root_x] + 1;
    }

    dsu["count"] = dsu["count"] - 1;
    return true;
}

fn dsu_connected(dsu: dict, x: int, y: int) -> bool {
    return dsu_find(dsu, x) == dsu_find(dsu, y);
}
```

---

## 4. Verification and Execution

Run compiler checks and the test suite:

```powershell
# 1. Run interactive network topology demo
lateralus_lang run examples/disjoint_set_tutorial.ltl

# 2. Run compiler check and unit test suite
lateralus_lang check tests/stdlib_disjoint_set_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus Disjoint Set Union (DSU) Network Pipeline Demo ===
Initialized 5 isolated network switches. Disjoint clusters: 5
Adding Fiber Cable (0 <-> 1) -> Success: true
Adding Fiber Cable (1 <-> 2) -> Success: true
Spanning Tree Guard: Attempting cable (0 <-> 2) -> false
Adding Fiber Cable (3 <-> 4) -> Success: true
Current Island Subnets: 2
Deploying Backbone Trunk (2 <-> 3) -> Success: true
Unified Network Topology Established! Total Disjoint Clusters: 1

DSU graph connectivity and spanning tree invariants verified 100% faithful!
```

---

## 5. Summary

Disjoint Set Union exemplifies how combining two minimal heuristics—path compression and rank balancing—transforms an $O(N)$ data structure into an effectively $O(1)$ powerhouse. Lateralus's flexible dictionaries and fast list mutations provide an optimal environment for graph algorithms, network topology trackers, and equivalence partitioners.
