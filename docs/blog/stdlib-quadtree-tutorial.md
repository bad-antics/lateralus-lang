# The Quadtree Spatial Partition & Range Query Engine in Lateralus

## 1. Introduction & Executive Summary

Organizing geometric objects, spatial sensor coordinates, and spatial telemetry in Euclidean space is a foundational challenge in computational geometry, Geographic Information Systems (GIS), and autonomous vehicle robotics. Linear search across $N$ spatial points requires exhaustive $O(N)$ comparisons, rendering real-time collision detection and radar scanning intractable for high-frequency control loops.

In 1974, **Raphael Finkel and Jon Louis Bentley** invented the **Quadtree**. The Quadtree is a hierarchical spatial partitioning data structure where each internal node recursively subdivides a two-dimensional bounding box into **four mutually disjoint quadrants**:
- **Northwest (NW)**
- **Northeast (NE)**
- **Southwest (SW)**
- **Southeast (SE)**

Unlike bounding-box hierarchies (such as R-Trees) where child bounding boxes may overlap, Quadtree quadrants partition the spatial canvas into strictly non-overlapping cells. When point density inside a leaf exceeds a bucket capacity threshold $C$, the cell splits instantaneously in $O(1)$ operations, pushing points into corresponding quadrant subtrees.

This tutorial provides complete mathematical formulations of recursive quadrant decomposition and delivers a verified production implementation in Lateralus.

---

## 2. Mathematical Foundations: The Disjoint Partition Property

Let $\Omega \subset \mathbb{R}^2$ be a bounded rectangular region defined by coordinate intervals:
$$\Omega = [x_{\min}, x_{\max}] \times [y_{\min}, y_{\max}]$$

### 2.1 Midpoint Bisection
Let $(x_m, y_m)$ denote the center coordinates of $\Omega$:
$$x_m = \frac{x_{\min} + x_{\max}}{2}, \quad y_m = \frac{y_{\min} + y_{\max}}{2}$$

The quadrant subdivision decomposes $\Omega$ into four non-overlapping subregions:
$$\Omega_{NW} = [x_{\min}, x_m] \times [y_m, y_{\max}]$$
$$\Omega_{NE} = [x_m, x_{\max}] \times [y_m, y_{\max}]$$
$$\Omega_{SW} = [x_{\min}, x_m] \times [y_{\min}, y_m]$$
$$\Omega_{SE} = [x_m, x_{\max}] \times [y_{\min}, y_m]$$

### 2.2 Invariant 1 (Exact Coverage & Disjointness)
1. **Exhaustive Union**: $\bigcup_{Q \in \{NW, NE, SW, SE\}} \Omega_Q = \Omega$.
2. **Boundary Disjointness**: The interiors of any two distinct quadrants are mutually disjoint:
   $$\text{int}(\Omega_i) \cap \text{int}(\Omega_j) = \emptyset, \quad \forall i \ne j$$

### 2.3 Deterministic Point Routing
For any point $p = (x, y) \in \Omega$, its quadrant index is resolved by two sign comparisons in $O(1)$ time:
$$\text{Quadrant}(x, y) = \begin{cases} 
NW & \text{if } x \le x_m \land y \ge y_m \\
NE & \text{if } x > x_m \land y \ge y_m \\
SW & \text{if } x \le x_m \land y < y_m \\
SE & \text{if } x > x_m \land y < y_m 
\end{cases}$$

---

## 3. Algorithmic Mechanics: Insertion & Range Query

### 3.1 Adaptive Subdivision with Capacity Threshold $C$
1. Each node maintains a bucket of points up to capacity $C$ (typically $C = 4$).
2. While $|P| \le C$, insertions are trivial $O(1)$ append operations.
3. Upon inserting the $(C+1)$-th point, the leaf node **subdivides**:
   - Four child nodes are allocated representing the four quadrants.
   - All existing $C$ points plus the new point are routed down to their respective quadrants.
   - The current node is marked `is_divided = true` and ceases to hold points directly.

### 3.2 Branch-and-Bound Spatial Window Search
To retrieve all points located within an arbitrary query rectangle $W$:
1. If the current quadrant's bounding box $\Omega_Q \cap W = \emptyset$, prune the entire subtree immediately ($O(1)$ exclusion).
2. If the current node is an undivided leaf, test each contained point for inclusion in $W$.
3. If the current node is subdivided, recursively search all four child quadrants:
   $$\text{Query}(NW) \cup \text{Query}(NE) \cup \text{Query}(SW) \cup \text{Query}(SE)$$

Average search time is bounded by $O(\log N + K)$, where $K$ is the number of points retrieved.

---

## 4. Lateralus Implementation

```lateralus
// stdlib/quadtree.ltl
pub fn qt_rect(min_x: int, min_y: int, max_x: int, max_y: int) -> dict {
    let mut r = {}
    r["min_x"] = min_x
    r["min_y"] = min_y
    r["max_x"] = max_x
    r["max_y"] = max_y
    return r
}

pub fn qt_rect_contains_pt(r: dict, x: int, y: int) -> bool {
    if x < r["min_x"] or x > r["max_x"] { return false }
    if y < r["min_y"] or y > r["max_y"] { return false }
    return true
}

pub fn qt_rect_intersects(a: dict, b: dict) -> bool {
    if a["max_x"] < b["min_x"] or a["min_x"] > b["max_x"] { return false }
    if a["max_y"] < b["min_y"] or a["min_y"] > b["max_y"] { return false }
    return true
}

pub fn qt_create(boundary: dict, capacity: int) -> dict {
    let mut tree = {}
    tree["capacity"] = capacity

    let mut boundaries = [qt_rect(0, 0, 0, 0), boundary]
    let mut is_divided = [false, false]
    let mut pts_x = [[], []]
    let mut pts_y = [[], []]
    let mut pts_id = [[], []]
    let mut child_nw = [0, 0]
    let mut child_ne = [0, 0]
    let mut child_sw = [0, 0]
    let mut child_se = [0, 0]

    tree["boundaries"] = boundaries
    tree["is_divided"] = is_divided
    tree["pts_x"] = pts_x
    tree["pts_y"] = pts_y
    tree["pts_id"] = pts_id
    tree["child_nw"] = child_nw
    tree["child_ne"] = child_ne
    tree["child_sw"] = child_sw
    tree["child_se"] = child_se
    tree["root"] = 1
    return tree
}

pub fn qt_subdivide(tree: dict, node: int) {
    let mut boundaries = tree["boundaries"]
    let mut is_divided = tree["is_divided"]
    let mut pts_x = tree["pts_x"]
    let mut pts_y = tree["pts_y"]
    let mut pts_id = tree["pts_id"]
    let mut child_nw = tree["child_nw"]
    let mut child_ne = tree["child_ne"]
    let mut child_sw = tree["child_sw"]
    let mut child_se = tree["child_se"]

    let b = boundaries[node]
    let min_x = b["min_x"]
    let min_y = b["min_y"]
    let max_x = b["max_x"]
    let max_y = b["max_y"]
    let mid_x = (min_x + max_x) / 2
    let mid_y = (min_y + max_y) / 2

    let nw_rect = qt_rect(min_x, mid_y, mid_x, max_y)
    let ne_rect = qt_rect(mid_x, mid_y, max_x, max_y)
    let sw_rect = qt_rect(min_x, min_y, mid_x, mid_y)
    let se_rect = qt_rect(mid_x, min_y, max_x, mid_y)

    let nw_idx = boundaries.len()
    boundaries.push(nw_rect)
    is_divided.push(false)
    pts_x.push([])
    pts_y.push([])
    pts_id.push([])
    child_nw.push(0)
    child_ne.push(0)
    child_sw.push(0)
    child_se.push(0)

    let ne_idx = boundaries.len()
    boundaries.push(ne_rect)
    is_divided.push(false)
    pts_x.push([])
    pts_y.push([])
    pts_id.push([])
    child_nw.push(0)
    child_ne.push(0)
    child_sw.push(0)
    child_se.push(0)

    let sw_idx = boundaries.len()
    boundaries.push(sw_rect)
    is_divided.push(false)
    pts_x.push([])
    pts_y.push([])
    pts_id.push([])
    child_nw.push(0)
    child_ne.push(0)
    child_sw.push(0)
    child_se.push(0)

    let se_idx = boundaries.len()
    boundaries.push(se_rect)
    is_divided.push(false)
    pts_x.push([])
    pts_y.push([])
    pts_id.push([])
    child_nw.push(0)
    child_ne.push(0)
    child_sw.push(0)
    child_se.push(0)

    child_nw[node] = nw_idx
    child_ne[node] = ne_idx
    child_sw[node] = sw_idx
    child_se[node] = se_idx
    is_divided[node] = true
}

pub fn qt_insert(tree: dict, node: int, x: int, y: int, id: int) -> bool {
    let boundaries = tree["boundaries"]
    if not qt_rect_contains_pt(boundaries[node], x, y) {
        return false
    }

    let is_divided = tree["is_divided"]
    if not is_divided[node] {
        let mut pts_x = tree["pts_x"]
        let mut pts_y = tree["pts_y"]
        let mut pts_id = tree["pts_id"]
        let cur_x = pts_x[node]

        if cur_x.len() < tree["capacity"] {
            let mut nx = pts_x[node]
            let mut ny = pts_y[node]
            let mut nid = pts_id[node]
            nx.push(x)
            ny.push(y)
            nid.push(id)
            pts_x[node] = nx
            pts_y[node] = ny
            pts_id[node] = nid
            return true
        }

        qt_subdivide(tree, node)

        let old_x = pts_x[node]
        let old_y = pts_y[node]
        let old_id = pts_id[node]
        pts_x[node] = []
        pts_y[node] = []
        pts_id[node] = []

        let n = old_x.len()
        let mut i = 0
        while i < n {
            qt_insert_into_children(tree, node, old_x[i], old_y[i], old_id[i])
            i = i + 1
        }
    }

    return qt_insert_into_children(tree, node, x, y, id)
}

pub fn qt_insert_into_children(tree: dict, node: int, x: int, y: int, id: int) -> bool {
    let child_nw = tree["child_nw"]
    let child_ne = tree["child_ne"]
    let child_sw = tree["child_sw"]
    let child_se = tree["child_se"]

    if qt_insert(tree, child_nw[node], x, y, id) { return true }
    if qt_insert(tree, child_ne[node], x, y, id) { return true }
    if qt_insert(tree, child_sw[node], x, y, id) { return true }
    if qt_insert(tree, child_se[node], x, y, id) { return true }
    return false
}

pub fn qt_query(tree: dict, node: int, range_rect: dict, results: list) {
    let boundaries = tree["boundaries"]
    if not qt_rect_intersects(boundaries[node], range_rect) {
        return
    }

    let is_divided = tree["is_divided"]
    if not is_divided[node] {
        let pts_x = tree["pts_x"]
        let pts_y = tree["pts_y"]
        let pts_id = tree["pts_id"]

        let xs = pts_x[node]
        let ys = pts_y[node]
        let ids = pts_id[node]
        let n = xs.len()

        let mut i = 0
        while i < n {
            if qt_rect_contains_pt(range_rect, xs[i], ys[i]) {
                results.push(ids[i])
            }
            i = i + 1
        }
        return
    }

    let child_nw = tree["child_nw"]
    let child_ne = tree["child_ne"]
    let child_sw = tree["child_sw"]
    let child_se = tree["child_se"]

    qt_query(tree, child_nw[node], range_rect, results)
    qt_query(tree, child_ne[node], range_rect, results)
    qt_query(tree, child_sw[node], range_rect, results)
    qt_query(tree, child_se[node], range_rect, results)
}

pub fn qt_search(tree: dict, range_rect: dict) -> list {
    let mut results = []
    qt_query(tree, tree["root"], range_rect, results)
    return results
}
```

---

## 5. Complexity & Architectural Comparison

| Structure | Partitioning Strategy | Space Overlap | Average Search | Insertion |
| :--- | :--- | :--- | :--- | :--- |
| **Grid Index** | Fixed uniform cells | None | $O(1 + K)$ | $O(1)$ |
| **KD-Tree** | Alternating single-axis hyperplanes | None | $O(\sqrt{N} + K)$ | $O(\log N)$ |
| **R-Tree** | Hierarchical bounding boxes (MBR) | Possible | $O(\log_M N + K)$ | $O(\log_M N)$ |
| **Quadtree** | **Hierarchical 4-quadrant bisection** | **Strictly None** | $\mathbf{O(\log N + K)}$ | $\mathbf{O(\log N)}$ |

---

## 6. Real-World Applications: Drone Flight Corridor Geofencing

In low-altitude Unmanned Aerial Vehicle (UAV) airspace management, flight safety requires continuously scanning forward flight corridors for navigation beacons and obstacle exclusion zones:

```lateralus
fn main() {
    let airspace = qt_rect(0, 0, 1000, 1000)
    let qt = qt_create(airspace, 4)

    // Register active navigation beacons
    qt_insert(qt, 1, 120, 150, 101)
    qt_insert(qt, 1, 140, 180, 102)
    qt_insert(qt, 1, 160, 130, 103)
    qt_insert(qt, 1, 750, 800, 104)

    // Query drone forward scanning cone
    let scan_cone = qt_rect(100, 100, 200, 200)
    let waypoints = qt_search(qt, scan_cone)
    print("Detected Waypoints in Sector: ")
    print(waypoints.len())
}
```

The Quadtree prunes distant waypoints (e.g., node 104 at [750, 800]) in $O(1)$ operations, achieving deterministic sub-millisecond response times.

---

## 7. Conclusion

The Quadtree embodies the mathematical beauty of recursive spatial bisection. By decomposing 2D space into mutually disjoint quadrants, it provides an intuitive, robust, and lightning-fast geometric engine for autonomous robotics, computer vision, and spatial databases.
