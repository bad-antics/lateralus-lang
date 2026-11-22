# Linear Algebra with `stdlib/linalg.ltl`

Vectors as lists, matrices as nested lists, and the operations you'd
expect: arithmetic, dot/cross products, magnitude/normalize, angles and
projections — plus matrix multiply, transpose, trace, 2×2/3×3
determinants, and LU decomposition with a linear solver.

`stdlib/linalg.ltl` wraps these as ergonomic functions over the built-in
math primitives. This tutorial works through the whole surface with
hand-checkable examples. Companion: `examples/linalg_tutorial.ltl`.

---

## Vectors

Vectors are plain `list`s of numbers — `[1.0, 2.0, 3.0]`. Element-wise
ops (`vec_add`, `vec_sub`, `vec_scale`) are simple loops; the interesting
ones are the reductions:

- **`dot_product(a, b)`** = Σ aᵢ·bᵢ — `[1,2,3]·[4,5,6] = 32`
- **`cross_product(a, b)`** — 3D only, returns the perpendicular vector;
  `î × ĵ = k̂` gives `[0,0,1]`
- **`magnitude(v)`** = √(v·v) — the 3-4-5 triangle gives exactly `5.0`
- **`normalize(v)`** = v/|v| — direction without magnitude; `[3,4]` →
  `[0.6, 0.8]` (prints `0.6000000000000001` — binary floating point, pin
  the actual repr)
- **`angle_between(a, b)`** = acos((a·b)/(|a||b|)), with the cosine
  clamped to [-1,1] so rounding can't produce NaN — `[1,0]` vs `[0,1]`
  gives π/2 ≈ `1.5707963267948966`
- **`projection(a, b)`** = b·(a·b)/(b·b) — `[3,4]` onto `[1,0]` gives
  `[3,0]`: the part of `a` that lies along `b`

The zero-vector guards matter: `normalize` and `angle_between` throw on
degenerate input rather than returning NaN silently. (The companion
returns a zero vector instead of throwing, keeping the demo total.)

## Matrices

Matrices are row-major nested lists. `mat_zeros`/`mat_identity` build
them; the ops mirror the vector ones one dimension up:

```text
mat_mul(A, B)[i][j] = sum_k A[i][k] * B[k][j]   -- i,j,k triple loop
mat_transpose swaps [i][j] <-> [j][i]
mat_trace = sum of diagonal
```

Determinants are hardcoded for the sizes people actually hit:
`mat_det_2x2` (ad − bc) and `mat_det_3x3` (cofactor expansion). For
`[[1,2],[3,4]]`, det = −2 — the matrix is invertible but orientation-
reversing.

## LU decomposition and solving

`mat_lu` factors A = L·U by Doolittle's method (no pivoting): U gets the
upper triangle, L gets unit-diagonal multipliers. `mat_solve_lu` then
does forward substitution (Ly = b) and back substitution (Ux = y) —
the standard way to solve Ax = b once you've paid for the factorization.

For `A = [[3,1],[1,2]]`, `b = [9,8]` the solution is `x = [2,3]` —
verify: 3·2+1·3 = 9, 1·2+2·3 = 8. ✓

Two caveats the module inherits from the algorithm: **no pivoting**
means near-singular matrices can divide by ~0 (it checks
`|U[j][j]| < 1e-12` and throws "singular"), and it's dense O(n³) — fine
for small systems, reach for an actual LAPACK binding for big ones.

## Running the companion

```text
STEP 1 add=[5.0, 7.0, 9.0] sub=[3.0, 3.0, 3.0]
STEP 1 scale 2x=[2.0, 4.0, 6.0]
STEP 2 dot=32.0
STEP 2 cross i^j=[0.0, 0.0, 1.0]
STEP 3 |v|=5.0 normalized=[0.6000000000000001, 0.8]
STEP 3 angle i,j=1.5707963267948966
STEP 3 proj [3,4] onto [1,0]=[3.0, 0.0]
STEP 4 A+B=[6.0, 8.0] ; [10.0, 12.0]
STEP 4 A*B=[19.0, 22.0] ; [43.0, 50.0]
STEP 4 At=[1.0, 3.0] ; [2.0, 4.0]
STEP 4 trace(A)=5.0 det2(A)=-2.0
STEP 5 det3(diag 2,3,4)=24.0
STEP 6 solve [[3,1],[1,2]] x = [9,8] -> [2.0, 3.0]
PINNED_VECTORS: dot=32.0 cross=0.0,0.0,1.0 mag=5.0 norm=0.6000000000000001,0.8 angle=1.5707963267948966 proj=3.0,0.0 det2=-2.0 det3=24.0 sol=2.0,3.0
```

`tests/test_linalg_tutorial.py` pins every line — including the
`0.6000000000000001` normalize artifact, which is the correct IEEE-754
result and exactly the kind of thing a pinned vector should catch.

## When to use it

**Use it** for small dense problems: game physics vectors, 2D/3D
transforms, tiny linear systems, teaching numeric code. Everything is
interpreted lists — no BLAS, no SIMD — so keep n modest.

**Don't use it** for large or sparse matrices, eigenproblems, SVD, or
anything iterative — the module covers the direct-method core only.
That's the right scope: learn the algorithms here, then reach for
LAPACK/NumPy bindings when size demands it.

That is `stdlib/linalg.ltl`: nineteen functions, row-major lists, and a
solver you can verify by hand.
