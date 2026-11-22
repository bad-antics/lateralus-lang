# Standard Library Deep Dive: Graham Scan 2D Convex Hull Algorithm

The **Convex Hull** of a finite set of points in the two-dimensional Euclidean plane is the smallest convex polygon that encloses all points. Introduced by Ronald Graham in 1972, the **Graham Scan** algorithm represents a foundational milestone in computational geometry, solving the planar convex hull problem in optimal **$O(n \log n)$** time and **$O(n)$** space.

---

## 1. Mathematical Principle: 2D Cross Products & Turn Direction

The orientation of any ordered triplet of planar points $(P_1, P_2, P_3)$ is determined by the sign of the 2D cross product of vectors $\vec{P_1 P_2}$ and $\vec{P_2 P_3}$:

$$\text{Cross}(P_1, P_2, P_3) = (x_2 - x_1)(y_3 - y_2) - (y_2 - y_1)(x_3 - x_2)$$

- **$\text{Cross} > 0$**: Points form a strictly **Counter-Clockwise (CCW)** turn (Left Turn).
- **$\text{Cross} < 0$**: Points form a **Clockwise (CW)** turn (Right Turn, creating an internal concave dent).
- **$\text{Cross} = 0$**: Points are **Collinear**.

```
       P3 (Left Turn, CCW > 0)
      /
     P2
    /
   P1       P2
          /    \
        P1      P3 (Right Turn, CW < 0 -> Pruned!)
```

---

## 2. Four-Phase Algorithmic Pipeline

### Phase 1: Pivot Selection
Locate point $P_0$ with the minimum $y$-coordinate (breaking ties by choosing the smallest $x$-coordinate). Because no point lies below $P_0$, it is mathematically guaranteed to be an external vertex on the convex hull.

### Phase 2: Polar Angle Sorting ($O(n \log n)$)
Sort all remaining points $P_1, \dots, P_{n-1}$ by their polar angle with respect to pivot $P_0$. The relative polar angle between points $A$ and $B$ is evaluated without floating-point trigonometry via $\text{Cross}(P_0, A, B)$:
- If $\text{Cross}(P_0, A, B) > 0$, point $A$ has a smaller polar angle than $B$.
- If collinear, the closer point to $P_0$ is ordered first.

### Phase 3: Monotonic Stack Maintenance ($O(n)$)
Initialize stack $H = [P_0, \text{sorted}[0]]$.
For each subsequent point $P_i$:
- While $|H| \ge 2$ and $\text{Cross}(H[\text{top}-1], H[\text{top}], P_i) \le 0$:
  Pop the stack top (as it creates a right turn or non-strict collinear edge).
- Push $P_i$ onto the stack.

### Phase 4: Output Enclosure
Upon processing all points, stack $H$ contains the convex hull vertices ordered in counter-clockwise sequence.

---

## 3. Lateralus Reference Implementation

```lateralus
fn cross_product(o, a, b) {
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
}

pub fn graham_scan(points) {
    let n = len(points)
    if n <= 3 {
        return points
    }

    let pivot_idx = 0
    let i = 1
    while i < n {
        let pt = points[i]
        let piv = points[pivot_idx]
        if pt[1] < piv[1] or (pt[1] == piv[1] and pt[0] < piv[0]) {
            pivot_idx = i
        }
        i = i + 1
    }

    let pivot = points[pivot_idx]

    let others = []
    let j = 0
    while j < n {
        if j != pivot_idx {
            others = push(others, points[j])
        }
        j = j + 1
    }

    let m = len(others)
    let a = 1
    while a < m {
        let key = others[a]
        let b = a - 1
        while b >= 0 {
            let prev = others[b]
            if compare_polar(pivot, prev, key) > 0 {
                others[b + 1] = prev
                b = b - 1
            } else {
                break
            }
        }
        others[b + 1] = key
        a = a + 1
    }

    let hull = [pivot, others[0]]
    let k = 1
    while k < m {
        let pt = others[k]
        while len(hull) >= 2 {
            let h_len = len(hull)
            let p1 = hull[h_len - 2]
            let p2 = hull[h_len - 1]
            if cross_product(p1, p2, pt) <= 0 {
                let new_hull = []
                let h_idx = 0
                while h_idx < h_len - 1 {
                    new_hull = push(new_hull, hull[h_idx])
                    h_idx = h_idx + 1
                }
                hull = new_hull
            } else {
                break
            }
        }
        hull = push(hull, pt)
        k = k + 1
    }

    return hull
}
```

---

## 4. Complexity & Resource Bounds

| Phase | Time Complexity | Invariant |
| :--- | :---: | :--- |
| **Pivot Selection** | $O(n)$ | Minimum linear search |
| **Polar Angle Sort** | $O(n \log n)$ | Asymptotically dominates execution |
| **Stack Back-tracking** | $O(n)$ | Each point pushed and popped $\le 1$ time |
| **Total Pipeline** | **$O(n \log n)$** | **Optimal theoretical lower bound** |

---

## 5. Industrial Applications

1. **Autonomous Drone & Robotics Path Planning**:
   Computing minimum convex safety collision buffers around clustered physical obstacles.
2. **GIS & Telematics Geofencing**:
   Generating boundary polygons enclosing fleet vehicle GPS coordinates for automated perimeter entry/exit alerts.
3. **Computer Graphics & Physics Engines**:
   Constructing tight bounding hulls for fast broad-phase collision detection in 2D simulation environments.
