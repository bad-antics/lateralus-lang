# Topological Sort Tutorial: Dependency Resolution and Kahn's Algorithm

## Overview

A **Topological Sort** of a directed graph is a linear ordering of its vertices such that for every directed edge $u \to v$, vertex $u$ comes before $v$ in the ordering. Topological sorting is only possible if and only if the graph has no directed cycles, making it a **Directed Acyclic Graph (DAG)**.

In Lateralus, topological sorting is essential for:
- **Build Pipelines and Compilers**: Determining valid compilation order for modules, AST lowering passes, and linker dependencies.
- **Task Scheduling and Orchestration**: Resolving DAG workflow execution plans with zero race conditions.
- **Distributed State Machines**: Linearizing transaction dependencies and state transition verification.
- **Deadlock and Circular Dependency Detection**: Identifying invalid cyclic references at compile-time or runtime.

---

## Kahn's Algorithm

Kahn's algorithm (introduced by Arthur Kahn in 1962) computes the topological order using vertex in-degrees (number of incoming directed edges):

1. **Calculate In-Degrees**: Count the number of incoming edges $\text{in\_degree}[v]$ for every vertex $v$.
2. **Initialize Queue**: Enqueue all vertices with $\text{in\_degree}[v] = 0$ (vertices with no dependencies).
3. **Process Vertices**:
   - Dequeue vertex $u$ and append it to the topological order list.
   - For every outgoing edge $u \to v$, decrement $\text{in\_degree}[v]$ by 1.
   - If $\text{in\_degree}[v]$ reaches 0, enqueue $v$.
4. **Cycle Verification**:
   - If the total count of processed vertices equals $|V|$, the graph is a valid DAG.
   - If fewer than $|V|$ vertices were processed, the graph contains at least one directed cycle (deadlock / circular dependency).

Time complexity is $O(|V| + |E|)$ and auxiliary space is $O(|V|)$.

---

## Lateralus Implementation

```lateralus
fn toposort(n: int, adj: dict) -> dict {
    let mut in_degree = [];
    let mut i = 0;
    while i < n {
        in_degree = in_degree + [0];
        i = i + 1;
    }

    let mut u = 0;
    while u < n {
        if contains(adj, u) {
            let targets = adj[u];
            let mut j = 0;
            while j < len(targets) {
                let v = targets[j];
                in_degree[v] = in_degree[v] + 1;
                j = j + 1;
            }
        }
        u = u + 1;
    }

    let mut queue = [];
    let mut q_head = 0;
    let mut k = 0;
    while k < n {
        if in_degree[k] == 0 {
            queue = queue + [k];
        }
        k = k + 1;
    }

    let mut order = [];
    while q_head < len(queue) {
        let curr = queue[q_head];
        q_head = q_head + 1;
        order = order + [curr];

        if contains(adj, curr) {
            let neighbors = adj[curr];
            let mut m = 0;
            while m < len(neighbors) {
                let nxt = neighbors[m];
                in_degree[nxt] = in_degree[nxt] - 1;
                if in_degree[nxt] == 0 {
                    queue = queue + [nxt];
                }
                m = m + 1;
            }
        }
    }

    let mut result = {};
    result["order"] = order;
    result["is_dag"] = (len(order) == n);
    return result;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_toposort_tutorial.ltl` verifies:

1. **Compiler Pipeline DAG**:
   - Validates strict dependency ordering across 6 stages: lexer $\to$ parser $\to$ ast $\to$ typechecker $\to$ optimizer $\to$ codegen.
2. **Cycle Detection**:
   - Detects cyclic subgraph ($0 \to 1 \to 2 \to 0$) returning `is_dag = false` and halting early.
3. **Disconnected DAG Components**:
   - Verifies handling of independent parallel dependency chains without starvation.
4. **Isolated Vertices**:
   - Verifies single-node graphs and graphs without edges.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_toposort_tutorial.ltl
python -m lateralus_lang check examples/toposort_tutorial.ltl
pytest tests/test_compiler.py
```
