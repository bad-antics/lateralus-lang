# Standard Library Deep Dive: Fractional Knapsack Greedy Optimization

The **Fractional Knapsack Problem** is a foundational model in algorithmic optimization, operations research, and resource scheduling. Unlike the 0-1 Knapsack problem (which is NP-complete and demands dynamic programming or branch-and-bound), the fractional variant allows items to be broken into arbitrary continuous fractions $x_i \in [0, 1]$.

This continuous relaxation enables an optimal solution via a **greedy algorithm** in deterministic **$O(n \log n)$** time and **$O(n)$** space.

---

## 1. Mathematical Formulation & Value Density

Given $n$ items, where item $i$ has value $v_i > 0$ and weight $w_i > 0$, and a knapsack with maximum weight capacity $W$:

$$\text{Maximize} \quad \sum_{i=1}^{n} x_i \cdot v_i \quad \text{subject to} \quad \sum_{i=1}^{n} x_i \cdot w_i \le W, \quad x_i \in [0, 1]$$

### The Value Density Metric
Define the value-to-weight ratio (density) of item $i$:

$$\rho_i = \frac{v_i}{w_i}$$

Sort items in descending order of density:

$$\rho_1 \ge \rho_2 \ge \dots \ge \rho_n$$

The greedy strategy repeatedly takes as much of the highest-density available item as possible until the capacity $W$ is saturated.

---

## 2. Rigorous Optimality Proof via Exchange Argument

We prove by contradiction that the greedy solution $G = (g_1, g_2, \dots, g_n)$ achieves the global maximum value $V(G)$.

1. Suppose there exists an optimal solution $O = (o_1, o_2, \dots, o_n)$ such that $V(O) > V(G)$.
2. Let $k$ be the first index where $g_k \ne o_k$. By greedy definition, $g_k > o_k$ (the greedy algorithm takes as much of the highest available density item $k$ as remaining capacity allows).
3. Since $\sum o_i w_i \le W$, there must exist some subsequent item $j > k$ such that $o_j > 0$ (some lower-density item was selected in $O$).
4. By our sorted order, $\rho_k \ge \rho_j$.
5. Consider replacing an amount of weight $\Delta w = \min(w_k(g_k - o_k), w_j o_j)$ of item $j$ with an equal weight of item $k$ in solution $O$. The total weight remains unchanged, but the value changes by:
   $$\Delta V = \Delta w \cdot (\rho_k - \rho_j) \ge 0$$
6. Repeating this exchange transforms $O$ into $G$ without ever decreasing the total value:
   $$V(G) \ge V(O)$$
7. Therefore, the greedy solution $G$ is strictly optimal. $\blacksquare$

---

## 3. Lateralus Reference Implementation

```lateralus
fn compare_density(item1, item2) {
    let v1 = item1[0]
    let w1 = item1[1]
    let v2 = item2[0]
    let w2 = item2[1]
    let cross1 = v1 * w2
    let cross2 = v2 * w1
    if cross1 > cross2 {
        return -1
    }
    if cross1 < cross2 {
        return 1
    }
    return 0
}

pub fn fractional_knapsack_scaled(items_in, capacity) {
    let n = len(items_in)
    let items = []
    let c = 0
    while c < n {
        items = push(items, items_in[c])
        c = c + 1
    }

    let a = 1
    while a < n {
        let key = items[a]
        let b = a - 1
        while b >= 0 {
            let prev = items[b]
            if compare_density(prev, key) > 0 {
                items[b + 1] = prev
                b = b - 1
            } else {
                break
            }
        }
        items[b + 1] = key
        a = a + 1
    }

    let remaining_cap = capacity
    let total_val_scaled = 0
    let fractions = []
    let i = 0

    while i < n and remaining_cap > 0 {
        let item = items[i]
        let v = item[0]
        let w = item[1]

        if w <= remaining_cap {
            remaining_cap = remaining_cap - w
            total_val_scaled = total_val_scaled + v * 1000
            fractions = push(fractions, [item[2], 1000])
        } else {
            let fraction_permille = (remaining_cap * 1000) / w
            total_val_scaled = total_val_scaled + (v * fraction_permille)
            fractions = push(fractions, [item[2], fraction_permille])
            remaining_cap = 0
        }
        i = i + 1
    }

    let res = dict()
    res["total_val_scaled"] = total_val_scaled
    res["fractions"] = fractions
    return res
}
```

---

## 4. Problem Duality: 0-1 Knapsack vs. Fractional Knapsack

| Dimension | 0-1 Knapsack | Fractional Knapsack |
| :--- | :---: | :---: |
| **Variable Domain** | $x_i \in \{0, 1\}$ (Discrete) | $x_i \in [0, 1]$ (Continuous) |
| **Complexity Class** | NP-Complete | $P$ (Polynomial) |
| **Algorithmic Strategy** | Dynamic Programming | Greedy Choice |
| **Time Complexity** | $O(n \cdot W)$ pseudo-polynomial | **$O(n \log n)$ strongly polynomial** |
| **Greedy Optimality** | Fails (Suboptimal counterexamples) | **Provably Global Optimal** |

---

## 5. Industrial Applications

1. **Cloud Computing Slicing**:
   Allocating fractions of physical compute/RAM resources to high-bidding Spot VM workloads to maximize cloud provider revenue.
2. **Logistics & Bulk Freight**:
   Loading bulk liquid, grain, or precious metals into transport containers subject to axle weight constraints.
3. **Portfolio Management**:
   Capital allocation across liquid asset classes to maximize Sharpe ratio under investment fund limits.
