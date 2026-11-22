# Convex Hull Tutorial: 2D Monotone Chain and Orientation Determinants

## Overview

In computational geometry, the **Convex Hull** of a set of points $S$ in the 2D Euclidean plane is the smallest convex polygon that encloses all points in $S$. Intuitively, if you imagine each point as a nail protruding from a board, the convex hull is the boundary formed by an elastic rubber band stretched around all the nails.

While the classical Graham scan algorithm (1972) computes angles or polar coordinates (which require trigonometric operations), **Andrew's Monotone Chain algorithm** (1979) sorts points lexicographically by their $(x, y)$ coordinates and builds the lower and upper hulls separately using strictly integer-based cross-product orientation tests.

In software engineering and spatial systems, convex hulls are used for:
- **Collision Detection & Game Physics**: Wrapping complex sprites/meshes in simple convex bounding hulls (e.g. separating axis theorem (SAT)).
- **GIS and Spatial Clustering**: Computing territorial boundaries, concave/convex envelopes of GPS coordinates.
- **Computer Vision & Pattern Recognition**: Object shape segmentation and hand gesture tracking.
- **Computational Economics**: Determining production-possibility frontiers.

---

## Geometric Foundations: The 2D Cross Product

Given three ordered points in the plane $O(x_0, y_0)$, $A(x_1, y_1)$, and $B(x_2, y_2)$, the 2D cross product of vectors $\vec{OA}$ and $\vec{OB}$ corresponds to the determinant:

$$\text{cross}(O, A, B) = (x_1 - x_0)(y_2 - y_0) - (y_1 - y_0)(x_2 - x_0)$$

- **$\text{cross} > 0$**: $\vec{OB}$ makes a **counter-clockwise (left) turn** from $\vec{OA}$.
- **$\text{cross} < 0$**: $\vec{OB}$ makes a **clockwise (right) turn** from $\vec{OA}$.
- **$\text{cross} = 0$**: The three points $O, A, B$ are **collinear**.

Because all operations are integer multiplications and subtractions, this eliminates floating-point precision error and edge-case jitter.

---

## Monotone Chain Algorithm

1. **Sort Points Lexicographically**:
   Sort points by $x$-coordinate; break ties by $y$-coordinate.
2. **Construct Lower Hull**:
   - Traverse sorted points from left to right.
   - For each point $P$, while the hull has at least 2 points and the last two points together with $P$ do not make a strictly counter-clockwise turn ($\text{cross}(lower[-2], lower[-1], P) \le 0$), pop the last point.
   - Append $P$.
3. **Construct Upper Hull**:
   - Traverse sorted points from right to left in reverse order.
   - Apply the same pop condition ($\text{cross} \le 0$) to eliminate concave vertices.
   - Append $P$.
4. **Merge**:
   - Concatenate the lower hull (excluding its last point) and the upper hull (excluding its last point) to form a closed cyclic polygon.

### Polygon Area via Shoelace Formula

The signed area of a polygon with vertices $(x_0, y_0), \dots, (x_{k-1}, y_{k-1})$ is given by Gauss's area formula:
$$2 \times \text{Area} = \left| \sum_{i=0}^{k-1} (x_i y_{i+1} - x_{i+1} y_i) \right|$$

---

## Lateralus Implementation

```lateralus
fn cross_product_2d(o: list, a: list, b: list) -> int {
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

fn sort_points(points: list) -> list {
    let mut pts = points;
    let n = len(pts);
    let mut i = 0;
    while i < n {
        let mut j = i + 1;
        while j < n {
            let p_i = pts[i];
            let p_j = pts[j];
            let mut swap = false;
            if p_j[0] < p_i[0] {
                swap = true;
            } else {
                if p_j[0] == p_i[0] && p_j[1] < p_i[1] {
                    swap = true;
                }
            }
            if swap {
                pts[i] = p_j;
                pts[j] = p_i;
            }
            j = j + 1;
        }
        i = i + 1;
    }
    return pts;
}

fn convex_hull(points: list) -> list {
    let n = len(points);
    if n <= 2 {
        return points;
    }

    let sorted = sort_points(points);

    // Build lower hull
    let mut lower = [];
    let mut i = 0;
    while i < n {
        let p = sorted[i];
        let mut can_pop = true;
        while len(lower) >= 2 && can_pop {
            let k = len(lower);
            let o = lower[k - 2];
            let a = lower[k - 1];
            if cross_product_2d(o, a, p) <= 0 {
                lower = slice(lower, 0, k - 1);
            } else {
                can_pop = false;
            }
        }
        lower = lower + [p];
        i = i + 1;
    }

    // Build upper hull
    let mut upper = [];
    let mut j = n - 1;
    while j >= 0 {
        let p = sorted[j];
        let mut can_pop_up = true;
        while len(upper) >= 2 && can_pop_up {
            let k2 = len(upper);
            let o2 = upper[k2 - 2];
            let a2 = upper[k2 - 1];
            if cross_product_2d(o2, a2, p) <= 0 {
                upper = slice(upper, 0, k2 - 1);
            } else {
                can_pop_up = false;
            }
        }
        upper = upper + [p];
        j = j - 1;
    }

    let lower_trimmed = slice(lower, 0, len(lower) - 1);
    let upper_trimmed = slice(upper, 0, len(upper) - 1);
    return lower_trimmed + upper_trimmed;
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_convex_hull_tutorial.ltl` validates:

1. **Orientation Test**:
   - Counter-clockwise turn yields $> 0$; clockwise turn yields $< 0$; collinear points yield 0.
2. **Unit Square Cloud**:
   - 8-point cloud with 4 corners and 4 interior points correctly simplifies to exactly the 4 corner points.
   - Shoelace double-area calculation correctly evaluates to 200 ($10 \times 10$ square).
3. **Triangle with Interior Point**:
   - Correctly discards interior centroid and measures exact double-area 36.
4. **Degenerate Point Pairs**:
   - $n = 2$ returns the point pair without crashing.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_convex_hull_tutorial.ltl
python -m lateralus_lang check examples/convex_hull_tutorial.ltl
pytest tests/test_compiler.py
```
