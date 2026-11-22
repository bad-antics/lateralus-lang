# 0/1 Knapsack Tutorial: Dynamic Programming and Block Packing Optimization

## Overview

The **0/1 Knapsack problem** is a canonical discrete combinatorial optimization problem. Given a set of $n$ items, each with a weight $w_i$ and a value $v_i$, and a maximum capacity $W$, the objective is to choose a subset of items to maximize total value without exceeding $W$, where each item must either be selected entirely (1) or left behind (0).

In distributed systems and decentralized ledger technology, the 0/1 Knapsack problem directly models:
- **Block Packing and Transaction Selection**: Maximizing miner/validator fee extraction within finite gas limits or block byte sizes (EIP-1559 priority fee optimization).
- **Resource Budgeting and Rate Limiting**: Allocating memory quotas or execution time slices across queued asynchronous worker tasks.
- **Cargo and Logistics Routing**: Maximizing cargo revenue subject to vehicle weight/volume boundaries.

---

## Dynamic Programming Formulation

The 0/1 Knapsack problem satisfies the **Principle of Optimality**: sub-problems exhibit optimal substructure.

Let $DP[i][w]$ represent the maximum value attainable using a subset of the first $i$ items within capacity constraint $w$.

### Bellman Recurrence Relation

For item $i$ with weight $w_i$ and value $v_i$:
1. If item $i$ is not included:
   $$DP[i][w] = DP[i-1][w]$$
2. If item $i$ is included (valid when $w_i \le w$):
   $$DP[i][w] = \max(DP[i-1][w], DP[i-1][w - w_i] + v_i)$$

Base cases:
$$DP[0][w] = 0 \quad \forall w \in [0, W]$$
$$DP[i][0] = 0 \quad \forall i \in [0, n]$$

### Exact Subset Reconstruction

To determine which exact items were selected:
- Start at $(i = n, w = W)$.
- If $DP[i][w] \neq DP[i-1][w]$, item $i-1$ was selected. We record item $i-1$ and decrement capacity $w \leftarrow w - w_{i-1}$.
- Decrement $i \leftarrow i - 1$ until $i = 0$.

Time complexity is $O(n \cdot W)$ and space complexity is $O(n \cdot W)$.

---

## Lateralus Implementation

```lateralus
fn knapsack_01(weights: list, values: list, capacity: int) -> dict {
    let n = len(weights);
    let mut dp = [];
    let mut i = 0;
    while i <= n {
        let mut row = [];
        let mut w = 0;
        while w <= capacity {
            row = row + [0];
            w = w + 1;
        }
        dp = dp + [row];
        i = i + 1;
    }

    let mut item = 1;
    while item <= n {
        let wt = weights[item - 1];
        let val = values[item - 1];
        let mut cap = 0;
        while cap <= capacity {
            if wt <= cap {
                let without_item = dp[item - 1][cap];
                let with_item = dp[item - 1][cap - wt] + val;
                if with_item > without_item {
                    dp[item][cap] = with_item;
                } else {
                    dp[item][cap] = without_item;
                }
            } else {
                dp[item][cap] = dp[item - 1][cap];
            }
            cap = cap + 1;
        }
        item = item + 1;
    }

    let max_val = dp[n][capacity];

    let mut selected = [];
    let mut curr_w = capacity;
    let mut k = n;
    while k > 0 {
        if dp[k][curr_w] != dp[k - 1][curr_w] {
            selected = [k - 1] + selected;
            curr_w = curr_w - weights[k - 1];
        }
        k = k - 1;
    }

    let mut result = {};
    result["max_value"] = max_val;
    result["selected"] = selected;
    return result;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_knapsack_tutorial.ltl` validates:

1. **Classical 4-Item Test Instance**:
   - Items with weights `[2, 3, 4, 5]` and values `[3, 4, 5, 6]`, capacity 5.
   - Verifies maximum value 7 and subset `[0, 1]`.
2. **5-Item Complex Instance**:
   - Verifies optimal choice selecting items 2 and 3 (weights 5+6=11, values 18+22=40).
3. **Zero Capacity Boundary**:
   - Returns 0 value and empty subset when capacity is 0.
4. **Capacity Exceeding Total Item Weight**:
   - Confirms selection of all items when capacity allows.
5. **Overweight Discards**:
   - Heavy items exceeding capacity discarded safely.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_knapsack_tutorial.ltl
python -m lateralus_lang check examples/knapsack_tutorial.ltl
pytest tests/test_compiler.py
```
