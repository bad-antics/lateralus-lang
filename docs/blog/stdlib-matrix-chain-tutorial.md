# Matrix Chain Multiplication Tutorial: Interval DP and Tensor Scheduling

## Overview

Matrix multiplication is associative, meaning $(A \cdot B) \cdot C = A \cdot (B \cdot C)$, but it is not commutative. Although the resulting matrix is identical regardless of parenthesization, the **computational cost (number of scalar multiplications)** varies dramatically depending on the evaluation order:

- Multiplying an $p \times q$ matrix by an $q \times r$ matrix requires $p \cdot q \cdot r$ scalar multiplications.
- Consider three matrices $A_1 (10 \times 100)$, $A_2 (100 \times 5)$, and $A_3 (5 \times 50)$:
  - Order $(A_1 A_2) A_3$: $10 \times 100 \times 5 + 10 \times 5 \times 50 = 5,000 + 2,500 = \mathbf{7,500}$ operations.
  - Order $A_1 (A_2 A_3)$: $100 \times 5 \times 50 + 10 \times 100 \times 50 = 25,000 + 50,000 = \mathbf{75,000}$ operations (10x slower!).

The **Matrix Chain Multiplication (MCM)** algorithm determines the parenthesization order that minimizes total operations in $O(n^3)$ time using interval dynamic programming.

In modern compiler and compute runtimes, MCM optimizes:
- **Deep Learning Tensor Compilers**: Automatic operator fusion and tensor contraction scheduling (e.g. Einstein summation in PyTorch / XLA).
- **3D Graphics Pipelines**: Multiplying model, view, projection, and viewport coordinate transformation matrices.
- **Relational Database Query Planners**: Ordering multi-way cross-table joins to minimize intermediate Cartesian product cardinality.

---

## Interval Dynamic Programming Formulation

Let the chain of $n$ matrices $A_1, A_2, \dots, A_n$ have dimensions given by array $P = [p_0, p_1, \dots, p_n]$, where matrix $A_i$ has dimension $p_{i-1} \times p_i$.

Let $M[i][j]$ denote the minimum number of scalar multiplications required to compute $A_i A_{i+1} \cdots A_j$.

### Optimal Substructure Recurrence

To compute $A_i \cdots A_j$, we must split the product at some intermediate point $k$ ($i \le k < j$):
$$(A_i \cdots A_k) \cdot (A_{k+1} \cdots A_j)$$

The cost of this split is:
$$\text{cost}(k) = M[i][k] + M[k+1][j] + p_{i-1} \cdot p_k \cdot p_j$$

Minimizing over all possible split points $k$:
$$M[i][j] = \begin{cases}
0 & \text{if } i = j \\
\min_{i \le k < j} \left( M[i][k] + M[k+1][j] + p_{i-1} \cdot p_k \cdot p_j \right) & \text{if } i < j
\end{cases}$$

### Tracking Split Matrix $S[i][j]$

Whenever a new minimum is achieved at split point $k$, we record $S[i][j] = k$. The optimal bracketed expression is then reconstructed recursively:
$$\text{build}(i, j) = \text{"("} + \text{build}(i, S[i][j]) + \text{" "} + \text{build}(S[i][j] + 1, j) + \text{")"}$$

Time complexity is $O(n^3)$ and auxiliary space is $O(n^2)$.

---

## Lateralus Implementation

```lateralus
fn build_parens(s: list, i: int, j: int) -> str {
    if i == j {
        return "A" + to_str(i);
    }
    let split = s[i][j];
    let left_str = build_parens(s, i, split);
    let right_str = build_parens(s, split + 1, j);
    return "(" + left_str + " " + right_str + ")";
}

fn matrix_chain_order(dims: list) -> dict {
    let num_dims = len(dims);
    let mut result = {};

    if num_dims <= 1 {
        result["min_cost"] = 0;
        result["parens"] = "";
        return result;
    }

    let n = num_dims - 1;
    let INF = 1000000000;

    let mut m = [];
    let mut s = [];
    let mut i = 0;
    while i <= n {
        let mut row_m = [];
        let mut row_s = [];
        let mut j = 0;
        while j <= n {
            row_m = row_m + [0];
            row_s = row_s + [0];
            j = j + 1;
        }
        m = m + [row_m];
        s = s + [row_s];
        i = i + 1;
    }

    let mut l = 2;
    while l <= n {
        let mut row = 1;
        while row <= (n - l + 1) {
            let col = row + l - 1;
            m[row][col] = INF;
            let mut k = row;
            while k < col {
                let cost = m[row][k] + m[k + 1][col] + dims[row - 1] * dims[k] * dims[col];
                if cost < m[row][col] {
                    m[row][col] = cost;
                    s[row][col] = k;
                }
                k = k + 1;
            }
            row = row + 1;
        }
        l = l + 1;
    }

    result["min_cost"] = m[1][n];
    result["parens"] = build_parens(s, 1, n);
    return result;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_matrix_chain_tutorial.ltl` validates:

1. **4-Matrix Classical Chain**:
   - `[10, 20, 30, 40, 30]` yields cost 30,000 and schedule `"(((A1 A2) A3) A4)"`.
2. **6-Matrix Complex Chain**:
   - `[30, 35, 15, 5, 10, 20, 25]` yields cost 15,125 and schedule `"((A1 (A2 A3)) ((A4 A5) A6))"`.
3. **2-Matrix Base Multiplication**:
   - `[10, 50, 20]` yields cost 10,000 and schedule `"(A1 A2)"`.
4. **Single-Matrix Boundary Case**:
   - `[10, 20]` yields cost 0 and schedule `"A1"`.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_matrix_chain_tutorial.ltl
python -m lateralus_lang check examples/matrix_chain_tutorial.ltl
pytest tests/test_compiler.py
```
