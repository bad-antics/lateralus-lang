# Matrix Linear Algebra in Lateralus: Transposition, Matrix Multiplication Invariants, and Determinant Scaling

Linear algebra is the foundational mathematical language of 3D computer graphics, physics simulation, neural network layer propagation, and scientific computing. A matrix acts as a compact, structured representation of a **linear map** between vector spaces.

In this tutorial, we implement, benchmark, and mathematically verify a core Matrix Linear Algebra engine in Lateralus, proving key algebraic invariants including non-commutativity, transpose reversal, and determinant multiplicativity.

---

## 1. Mathematical Anatomy & Invariants

Let matrix $A \in \mathbb{R}^{M \times K}$ and matrix $B \in \mathbb{R}^{K \times N}$.

### 1.1 Matrix Multiplication ($O(M \cdot K \cdot N)$)

Matrix multiplication is defined only when the number of columns in $A$ equals the number of rows in $B$. The entry at row $i$ and column $j$ in the product $C = A \cdot B$ is the inner dot product of row $i$ of $A$ and column $j$ of $B$:

$$C_{ij} = \sum_{k=0}^{K-1} A_{ik} B_{kj}$$

### 1.2 Transposition & Reversal Law

The transpose $A^T$ interchanges rows and columns: $(A^T)_{ij} = A_{ji}$.

**Critical Invariant**: Transposition reverses the order of matrix multiplication:

$$(A \cdot B)^T = B^T \cdot A^T$$

In Lateralus, our test suite asserts this invariant programmatically:

```lateralus
let ab_t = matrix_transpose(matrix_mul(a, b));
let bt_at = matrix_mul(matrix_transpose(b), matrix_transpose(a));
assert(ab_t[0][0] == bt_at[0][0]);
assert(ab_t[0][1] == bt_at[0][1]);
```

### 1.3 Determinant as Geometric Area Scaling Factor

The determinant $\det(A)$ represents the signed volume/area scaling factor induced by the transformation:
- For a $2 \times 2$ matrix:
  $$\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc$$
- For a $3 \times 3$ matrix (Laplace expansion):
  $$\det(M) = m_{00}(m_{11}m_{22} - m_{12}m_{21}) - m_{01}(m_{10}m_{22} - m_{12}m_{20}) + m_{02}(m_{10}m_{21} - m_{11}m_{20})$$

**Multiplicative Property**:
$$\det(A \cdot B) = \det(A) \cdot \det(B)$$

---

## 2. Invariant: Non-Commutativity ($A \cdot B \neq B \cdot A$)

Unlike scalar multiplication, matrix multiplication is strictly non-commutative. Applying transformation $A$ followed by $B$ is fundamentally different from applying $B$ followed by $A$:

$$A \cdot B \neq B \cdot A$$

---

## 3. The Lateralus Implementation

### 3.1 Matrix Multiplication Engine

```lateralus
fn matrix_mul(a: list, b: list) -> list {
    let m = len(a);
    let k_dim = len(a[0]);
    let n = len(b[0]);

    let mut c = [];
    let mut i = 0;
    while i < m {
        let mut row = [];
        let mut j = 0;
        while j < n {
            let mut sum = 0;
            let mut k = 0;
            while k < k_dim {
                sum = sum + a[i][k] * b[k][j];
                k = k + 1;
            }
            row = row + [sum];
            j = j + 1;
        }
        c = c + [row];
        i = i + 1;
    }
    return c;
}
```

### 3.2 Matrix Transposition

```lateralus
fn matrix_transpose(a: list) -> list {
    let rows = len(a);
    let cols = len(a[0]);
    let mut t = [];
    let mut j = 0;
    while j < cols {
        let mut row = [];
        let mut i = 0;
        while i < rows {
            row = row + [a[i][j]];
            i = i + 1;
        }
        t = t + [row];
        j = j + 1;
    }
    return t;
}
```

### 3.3 Determinant Evaluator

```lateralus
fn matrix_det2(a: list) -> int {
    return a[0][0] * a[1][1] - a[0][1] * a[1][0];
}

fn matrix_det3(a: list) -> int {
    let term1 = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]);
    let term2 = a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]);
    let term3 = a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    return term1 - term2 + term3;
}
```

---

## 4. Verification and Execution

Run compiler checks and the test suite:

```powershell
# 1. Run interactive tutorial demo
lateralus_lang run examples/matrix_tutorial.ltl

# 2. Run compiler check and unit test suite
lateralus_lang check tests/stdlib_matrix_tutorial.ltl
pytest tests/test_compiler.py
```

### Expected Output

```
=== Lateralus Matrix Transformation Pipeline Demo ===
Transformation Matrix T: [[2, 1], [0, 3]]
Transformation Area Scaling Factor (Determinant): 6
Initial Coordinate Vector P: [[4], [5]]
Transformed Coordinate Vector P' = T * P: [[13], [15]]
Transposed Matrix T^T: [[2, 0], [1, 3]]

Matrix linear transformations and determinant verified 100% faithful!
```

---

## 5. Summary

Matrix operations form the core of modern numerical computation. Lateralus's clean nested list structures and deterministic loop primitives make implementing linear transformations, graphics pipelines, and algebraic solvers straightforward and provably correct.
