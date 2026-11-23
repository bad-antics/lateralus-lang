# Standard Library Deep Dive: Dinic's Blocking Flow Maximum Network Flow Algorithm

The **Maximum Network Flow** problem is a fundamental challenge in combinatorial optimization, network engineering, and operations research. Given a directed flow network $G = (V, E)$ with source $s$, sink $t$, and edge capacities $c(u, v) \ge 0$, the goal is to maximize total material transported from $s$ to $t$ subject to capacity and conservation constraints.

While the classical Edmonds-Karp algorithm finds augmenting paths via BFS in $O(V \cdot E^2)$ time, **Dinic's Algorithm** (introduced by Yefim Dinitz in 1970) introduces the powerful dual-phase concepts of **Level Graphs** and **Blocking Flows**, slashing runtime complexity to **$O(V^2 \cdot E)$** on general networks and $O(E \sqrt{V})$ on unit-capacity bipartite networks.

---

## 1. Core Mathematical Constructs: Level Graphs & Blocking Flows

### 1.1 The Level Graph ($G_L$)
Constructed using Breadth-First Search (BFS) starting from source $s$:
- Each node $v$ is assigned its shortest distance from $s$ in the residual graph: $\text{level}[v]$.
- The **Level Graph** retains only directed residual edges $(u, v)$ where:
  $$\text{level}[v] = \text{level}[u] + 1 \quad \text{and} \quad \text{res}[u][v] > 0$$

Because levels increase strictly by $+1$ along every edge, the level graph is guaranteed to be a **Directed Acyclic Graph (DAG)**, completely eliminating circular backtracking.

```
Source (s, Level 0) ----> u (Level 1) ----> v (Level 2) ----> Sink (t, Level 3)
```

### 1.2 The Blocking Flow
Within the level DAG, Depth-First Search (DFS) pushes flow iteratively from $s$ to $t$ until no augmenting paths remain in $G_L$. A flow is **blocking** if every path from $s$ to $t$ in $G_L$ contains at least one saturated edge with residual capacity $0$.

---

## 2. Theoretical Complexity Proof: $O(V^2 \cdot E)$

1. **Strictly Increasing Phase Distance**:
   After finding a blocking flow in $G_L$, any new path from $s$ to $t$ in the residual graph must use at least one backward or cross-layer edge. Consequently, the shortest path distance $\text{level}[t]$ strictly increases by at least $+1$ in each iteration.
2. **Phase Count Bound**:
   Since the distance from $s$ to $t$ cannot exceed $|V| - 1$, the BFS phase occurs at most **$|V| - 1$ times**.
3. **Work Per Phase**:
   Each augmenting path saturates at least one bottleneck edge. Across a single phase, saturated edges are removed from the active level graph, ensuring the total time spent pushing flow across a single phase is bounded by $O(V \cdot E)$.
4. **Total Bound**:
   $$(\text{Phases} \le |V|) \times (\text{Work per phase} \le O(V \cdot E)) = O(V^2 \cdot E)$$

---

## 3. Lateralus Reference Implementation

```lateralus
fn bfs_level_graph(net, s, t, level) {
    let n = net["n"]
    let res = net["res"]
    let adj = net["adj"]

    let i = 0
    while i < n {
        level[i] = -1
        i = i + 1
    }

    level[s] = 0
    let queue = [s]
    let q_head = 0

    while q_head < len(queue) {
        let u = queue[q_head]
        q_head = q_head + 1

        let neighbors = adj[u]
        let k = 0
        while k < len(neighbors) {
            let v = neighbors[k]
            if level[v] == -1 and res[u][v] > 0 {
                level[v] = level[u] + 1
                queue = push(queue, v)
            }
            k = k + 1
        }
    }

    return level[t] != -1
}

fn send_blocking_flow(net, u, flow_in, t, level) {
    if u == t {
        return flow_in
    }

    let res = net["res"]
    let adj = net["adj"]
    let neighbors = adj[u]
    let k = 0

    while k < len(neighbors) {
        let v = neighbors[k]
        if level[v] == level[u] + 1 and res[u][v] > 0 {
            let curr_cap = min_val(flow_in, res[u][v])
            let pushed = send_blocking_flow(net, v, curr_cap, t, level)

            if pushed > 0 {
                res[u][v] = res[u][v] - pushed
                res[v][u] = res[v][u] + pushed
                return pushed
            }
        }
        k = k + 1
    }

    return 0
}

pub fn dinic_max_flow(net, s, t) {
    let total_flow = 0
    let level = dict()
    let inf_flow = 1000000000

    while bfs_level_graph(net, s, t, level) {
        while true {
            let pushed = send_blocking_flow(net, s, inf_flow, t, level)
            if pushed <= 0 {
                break
            }
            total_flow = total_flow + pushed
        }
    }

    return total_flow
}
```

---

## 4. Architectural Comparison

| Dimension | Ford-Fulkerson | Edmonds-Karp | Dinic's Algorithm |
| :--- | :---: | :---: | :---: |
| **Augmentation Strategy** | Arbitrary DFS path | Shortest BFS path | Blocking flow in level DAG |
| **Worst-Case Time** | $O(E \cdot F_{\max})$ | $O(V \cdot E^2)$ | **$O(V^2 \cdot E)$ (Optimal)** |
| **Unit Networks** | $O(E \cdot F_{\max})$ | $O(V \cdot E^2)$ | **$O(E \sqrt{V})$ (Bipartite optimal)** |
| **Capacity Dependence** | Yes (Can stall on real values) | Independent | Independent |

---

## 5. Industrial Applications

1. **Telecommunications Backhaul Scheduling**:
   Maximizing packet transit data rate across complex mesh networks of fiber optic cables and routers.
2. **Supply Chain & Freight Routing**:
   Evaluating the maximum daily cargo tonnage transportable across multi-hop aviation and rail hub networks.
3. **Computer Vision & Image Segmentation (Graph Cuts)**:
   Finding the global minimum cut between foreground and background pixels in $s-t$ cut image segmentations.
