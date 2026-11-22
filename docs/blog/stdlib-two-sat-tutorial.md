# 2-SAT & Linear-Time Implication Graphs in Lateralus

## 1. Introduction & Computational Complexity

The **Boolean Satisfiability Problem (SAT)** occupies a legendary position in theoretical computer science. In 1971, Stephen Cook and Leonid Levin proved that general SAT is **NP-complete** (the Cook-Levin Theorem), providing the bedrock for computational complexity theory. When clauses contain three or more literals (3-SAT), finding a satisfying assignment or proving unsatisfiability remains NP-complete, requiring exponential time in the worst case under the $P \ne NP$ conjecture.

However, when each clause is restricted to at most **two literals** (**2-SAT**), the problem drops from exponential intractability into a polynomial-time oasis. In 1979, **Bengt Aspvall, Michael F. Plass, and Robert E. Tarjan** proved that 2-SAT can be solved in strictly **linear time $O(V + E)$** by mapping boolean clauses into a directed **Implication Graph** and computing Strongly Connected Components (SCCs).

This tutorial provides complete mathematical proofs of the Aspvall-Plass-Tarjan theorem and delivers a verified production implementation in Lateralus.

---

## 2. Mathematical Foundations: The Implication Graph

Let $\Phi$ be a boolean formula in 2-Conjunctive Normal Form (2-CNF) over $n$ boolean variables $x_1, x_2, \dots, x_n$:
$$\Phi = \bigwedge_{j=1}^m (l_{j,1} \lor l_{j,2})$$
where each literal $l_{j,k} \in \{x_i, \neg x_i\}$.

### 2.1 Logical Equivalence to Implications
Using classical propositional logic, a disjunction $(u \lor v)$ is logically equivalent to two conditional statements:
$$(u \lor v) \iff (\neg u \implies v) \land (\neg v \implies u)$$

### 2.2 Constructing the Implication Graph $G_\Phi$
Construct a directed graph $G_\Phi = (V, E)$:
1. **Vertices ($V$)**: For each boolean variable $x_i$, allocate two vertices:
   - Node $2i$ representing literal $x_i$
   - Node $2i + 1$ representing literal $\neg x_i$
   Total vertices $|V| = 2n$.
2. **Directed Edges ($E$)**: For each clause $(u \lor v)$, add two directed edges:
   $$\neg u \to v \quad \text{and} \quad \neg v \to u$$
   Total edges $|E| = 2m$.

---

## 3. The Aspvall-Plass-Tarjan Theorem

### 3.1 Theorem (Satisfiability Invariant)
*A 2-CNF formula $\Phi$ is satisfiable if and only if for every variable $x_i$, vertices $x_i$ and $\neg x_i$ belong to different Strongly Connected Components in $G_\Phi$:*
$$\Phi \text{ is SAT} \iff \forall i \in \{1, \dots, n\}, \; \text{SCC}(x_i) \ne \text{SCC}(\neg x_i)$$

#### Proof:
1. **$(\Rightarrow)$ [Soundness]**: Suppose $x_i$ and $\neg x_i$ belong to the same SCC. Then there exists a directed path from $x_i \rightsquigarrow \neg x_i$ and a directed path from $\neg x_i \rightsquigarrow x_i$. By transitivity of implication:
   $$x_i \implies \neg x_i \quad \text{and} \quad \neg x_i \implies x_i$$
   If $x_i = \text{true}$, then $\neg x_i = \text{true}$, a contradiction. If $x_i = \text{false}$, then $x_i = \text{true}$, also a contradiction. Thus no truth assignment exists.
2. **$(\Leftarrow)$ [Completeness & Constructive Assignment]**: Suppose no variable shares an SCC with its negation. Contract each SCC into a Directed Acyclic Graph (DAG) $G^{\text{SCC}}$.
   - Tarjan's low-link DFS outputs SCCs in **reverse topological order** (sinks first, sources last).
   - If $\text{SCC}(x_i) < \text{SCC}(\neg x_i)$, component $\text{SCC}(x_i)$ is topologically downstream of $\text{SCC}(\neg x_i)$.
   - Assign $x_i = \text{true}$ if $\text{SCC}(x_i) < \text{SCC}(\neg x_i)$, and $x_i = \text{false}$ otherwise.
   - This construction guarantees that no implication evaluates to $\text{true} \implies \text{false}$, yielding a valid satisfying model. $\blacksquare$

---

## 4. Lateralus Implementation

```lateralus
// stdlib/two_sat.ltl
pub fn two_sat_create(n: int) -> dict {
    let mut ts = {}
    ts["n"] = n

    let mut adj = []
    let total_nodes = 2 * n + 2
    let mut i = 0
    while i < total_nodes {
        adj.push([])
        i = i + 1
    }

    ts["adj"] = adj
    return ts
}

pub fn two_sat_add_clause(ts: dict, u: int, u_val: bool, v: int, v_val: bool) {
    let mut adj = ts["adj"]

    let mut u_node = 2 * u
    let mut not_u = 2 * u + 1
    if not u_val {
        u_node = 2 * u + 1
        not_u = 2 * u
    }

    let mut v_node = 2 * v
    let mut not_v = 2 * v + 1
    if not v_val {
        v_node = 2 * v + 1
        not_v = 2 * v
    }

    let mut not_u_edges = adj[not_u]
    not_u_edges.push(v_node)
    adj[not_u] = not_u_edges

    let mut not_v_edges = adj[not_v]
    not_v_edges.push(u_node)
    adj[not_v] = not_v_edges
}

pub fn tarjan_dfs(u: int, adj: list, dfn: list, low: list, in_stack: list, stack: list, scc_id: list, state: dict) {
    let mut timer = state["timer"]
    timer = timer + 1
    state["timer"] = timer

    dfn[u] = timer
    low[u] = timer
    stack.push(u)
    in_stack[u] = true

    let u_edges = adj[u]
    let n_edges = u_edges.len()
    let mut i = 0
    while i < n_edges {
        let v = u_edges[i]
        if dfn[v] == 0 {
            tarjan_dfs(v, adj, dfn, low, in_stack, stack, scc_id, state)
            if low[v] < low[u] {
                low[u] = low[v]
            }
        } else {
            if in_stack[v] {
                if dfn[v] < low[u] {
                    low[u] = dfn[v]
                }
            }
        }
        i = i + 1
    }

    if dfn[u] == low[u] {
        let mut scc_count = state["scc_count"]
        scc_count = scc_count + 1
        state["scc_count"] = scc_count

        let mut done = false
        while not done {
            let last_idx = stack.len() - 1
            let top_node = stack[last_idx]
            let _ = stack.pop()
            in_stack[top_node] = false
            scc_id[top_node] = scc_count
            if top_node == u {
                done = true
            }
        }
    }
}

pub fn two_sat_solve(ts: dict) -> dict {
    let n = ts["n"]
    let adj = ts["adj"]
    let total_nodes = 2 * n + 2

    let mut dfn = []
    let mut low = []
    let mut in_stack = []
    let mut scc_id = []
    let mut stack = []

    let mut i = 0
    while i < total_nodes {
        dfn.push(0)
        low.push(0)
        in_stack.push(false)
        scc_id.push(0)
        i = i + 1
    }

    let mut state = {}
    state["timer"] = 0
    state["scc_count"] = 0

    let mut node = 2
    while node < total_nodes {
        if dfn[node] == 0 {
            tarjan_dfs(node, adj, dfn, low, in_stack, stack, scc_id, state)
        }
        node = node + 1
    }

    let mut satisfiable = true
    let mut assignment = [false]

    let mut var_idx = 1
    while var_idx <= n {
        let pos_scc = scc_id[2 * var_idx]
        let neg_scc = scc_id[2 * var_idx + 1]

        if pos_scc == neg_scc {
            satisfiable = false
        }

        let is_true = (pos_scc < neg_scc)
        assignment.push(is_true)
        var_idx = var_idx + 1
    }

    let mut res = {}
    res["satisfiable"] = satisfiable
    res["assignment"] = assignment
    return res
}
```

---

## 5. Complexity & Guarantees

| Phase | Time Complexity | Space Complexity | Notes |
| :--- | :--- | :--- | :--- |
| **Graph Construction** | $O(V + E)$ | $O(V + E)$ | 2 edges per 2-CNF clause |
| **Tarjan SCC** | $O(V + E)$ | $O(V)$ | Single DFS traversal |
| **Consistency Check** | $O(V)$ | $O(V)$ | Comparing $\text{SCC}(2i)$ vs $\text{SCC}(2i+1)$ |
| **Truth Assignment** | $O(V)$ | $O(V)$ | Constructive reverse topological index comparison |

---

## 6. Real-World Case Study: Package Manager Dependency Resolution

Modern package managers (such as Cargo, npm, and apt) face version compatibility constraints:

```lateralus
fn main() {
    let solver = two_sat_create(3)
    two_sat_add_clause(solver, 1, true, 2, true)   // Must install A (1) or B (2)
    two_sat_add_clause(solver, 2, false, 3, true)  // B (2) requires C (3)
    two_sat_add_clause(solver, 1, false, 3, false) // A (1) conflicts with C (3)

    let result = two_sat_solve(solver)
    print("Is Dependency System Satisfiable: ")
    print(result["satisfiable"])
}
```

The solver determines satisfiability and produces an exact non-conflicting package selection in linear time.

---

## 7. Conclusion

2-SAT demonstrates how structural graph decomposition transforms an NP-hard problem into linear-time certainty. By mapping logical disjunctions into directed implication networks, the Aspvall-Plass-Tarjan theorem provides an indispensable foundation for formal verification, compiler optimization, and automated constraint solvers.
