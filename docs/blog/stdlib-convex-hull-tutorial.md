---
title: "Convex Hull Tutorial"
author: bad-antics
date: 2026-04-07
abstract: Implementing the Monotone Chain algorithm for 2D convex hulls using cross-product orientation vectors.
---

# Convex Hull Tutorial

## Introduction

The convex hull of a set of 2D points is the smallest convex polygon that contains all the points. This tutorial implements Andrew's Monotone Chain algorithm (1979), which efficiently computes convex hulls in $O(n \log n)$ time using cross-product orientation tests.

## 2D Cross-Product Orientation Determinant

The cross-product orientation test determines the relative orientation of three points $A$, $B$, and $O$:

$$\text{orientation} = (A_x - O_x)(B_y - O_y) - (A_y - O_y)(B_x - O_x)$$

This determinant tells us whether the sequence of points $A \rightarrow B \rightarrow O$ makes a:
- **Counter-clockwise turn** if orientation > 0
- **Clockwise turn** if orientation < 0
- **Collinear** if orientation = 0

```ltl
fn cross_product(o: (float, float), a: (float, float), b: (float, float)) -> float {
    return (a.0 - o.0) * (b.1 - o.1) - (a.1 - o.1) * (b.0 - o.0)
}
```

## Monotone Chain Algorithm

The algorithm works by:
1. Sorting points lexicographically (by x, then by y)
2. Building the lower hull from left to right
3. Building the upper hull from right to left
4. Combining both hulls (removing duplicate endpoints)

### Building the Lower Hull

```ltl
fn build_lower_hull(points: list[(float, float)]) -> list[(float, float)] {
    let mut hull = []
    
    for point in points {
        while len(hull) >= 2 and 
              cross_product(hull[len(hull)-2], hull[len(hull)-1], point) <= 0 {
            hull.pop()
        }
        hull.push(point)
    }
    
    return hull
}
```

### Building the Upper Hull

```ltl
fn build_upper_hull(points: list[(float, float)]) -> list[(float, float)] {
    let mut hull = []
    
    for i from len(points)-1 down to 0 {
        let point = points[i]
        while len(hull) >= 2 and 
              cross_product(hull[len(hull)-2], hull[len(hull)-1], point) <= 0 {
            hull.pop()
        }
        hull.push(point)
    }
    
    return hull
}
```

### Combining Hulls

```ltl
fn convex_hull(points: list[(float, float)]) -> list[(float, float)] {
    if len(points) <= 1 {
        return points
    }
    
    let sorted_points = sort_lexicographically(points)
    let lower = build_lower_hull(sorted_points)
    let upper = build_upper_hull(sorted_points)
    
    // Remove duplicate endpoints
    let combined = lower[0:len(lower)-1] + upper[0:len(upper)-1]
    
    return combined
}
```

## Shoelace Formula for Polygon Area

To calculate the area of the convex hull polygon:

$$\text{Area} = \frac{1}{2} |\sum_{i=0}^{n-1} (x_i y_{i+1}) - \sum_{i=0}^{n-1} (y_i x_{i+1})|$$

```ltl
fn polygon_area(vertices: list[(float, float)]) -> float {
    let n = len(vertices)
    if n < 3 {
        return 0.0
    }
    
    let mut area = 0.0
    for i from 0 to n-1 {
        let j = (i + 1) % n
        area += vertices[i].0 * vertices[j].1
        area -= vertices[j].0 * vertices[i].1
    }
    
    return abs(area) / 2.0
}
```

## Practical Application: Collision Bounding Polygon

```ltl
// Generate collision bounding hull for game entities
fn generate_collision_hull(entities: list[(float, float)]) -> list[(float, float)] {
    return convex_hull(entities)
}

// Check if a point is inside the convex hull
fn point_in_hull(point: (float, float), hull: list[(float, float)]) -> bool {
    let n = len(hull)
    if n < 3 {
        return false
    }
    
    for i from 0 to n-1 {
        let j = (i + 1) % n
        if cross_product(hull[i], hull[j], point) < 0 {
            return false
        }
    }
    
    return true
}
```

## Conclusion

The Monotone Chain algorithm provides an efficient and robust method for computing convex hulls in 2D. By using cross-product orientation tests, we ensure exact geometric calculations without floating-point precision issues. This implementation is particularly valuable for collision detection, boundary estimation, and other computational geometry applications.
