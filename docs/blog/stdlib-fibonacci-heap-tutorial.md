# Fibonacci Heap & $O(1)$ Amortized Key-Reduction in Lateralus

## 1. Introduction & Executive Summary

In algorithmic graph theory and network optimization, the Priority Queue is the primary performance bottleneck for greedy algorithms, including Dijkstra's Single-Source Shortest Path (SSSP) and Prim's Minimum Spanning Tree (MST). When routing across dense communication topologies, power grids, or transportation roadmaps with $|V|$ vertices and $|E|$ edges, standard priority queues incur substantial overhead:

- A standard **Binary Heap** executes both `extract_min` and `decrease_key` in $O(\log V)$ time. Running Dijkstra requires $|V|$ extractions and up to $|E|$ key relaxations, yielding total runtime:
  $$T_{\text{binary}}(V, E) = O((V + E) \log V)$$
- When $|E| = \Theta(V^2)$ (dense networks), this degrades to $O(V^2 \log V)$.

In their landmark paper, **Michael L. Fredman and Robert E. Tarjan (1987)** introduced the **Fibonacci Heap**, which dramatically decouples key relaxations from tree balancing. By employing **lazy consolidation** and **cascading cuts**, the Fibonacci Heap reduces the amortized cost of `insert`, `meld`, and `decrease_key` to strict **$O(1)$ constant time**, retaining $O(\log n)$ only for `extract_min`. Consequently, Dijkstra's algorithm reaches its theoretical asymptotic minimum:
$$T_{\text{fibonacci}}(V, E) = O(E + V \log V)$$
On dense graphs, this yields optimal $O(V^2)$ performance, saving millions of CPU cycles in high-frequency network routing engines.

This tutorial explores the algebraic and combinatorial mechanics behind Fibonacci Heaps and provides a complete implementation in Lateralus.

---

## 2. Structural Topology & Algorithmic Mechanics

### 2.1 Circular Doubly-Linked Lists and Lazy Strategy

Unlike binary heaps with rigid shape invariants, a Fibonacci Heap is a collection of min-heap-ordered trees arranged in a **circular doubly-linked root list**.

```
    min_node
       |
       v
    [Node 12] <---> [Node 45] <---> [Node 67]
     /      \             |
 [Node 18] [Node 35]   [Node 80]
     |
 [Node 24]
```

1. **Lazy Insertion**: When a new key is inserted via `fib_insert`, it is simply appended to the root list in $O(1)$ time without examining existing tree depths.
2. **Lazy Merging**: Two heaps are melded via `fib_meld` by splicing their root lists together in $O(1)$ time.
3. **Consolidation on Extraction**: All structural housekeeping is deferred until `fib_extract_min`.

---

### 2.2 Extract-Min & Degree Consolidation

When `fib_extract_min` removes the minimum root:
1. All direct children of the minimum node are unparented and spliced into the root list.
2. The minimum node is removed.
3. **Degree Consolidation** begins: An auxiliary array $A[0 \dots D(n)]$ tracks roots by their degrees. The algorithm scans the root list; whenever two trees $T_1$ and $T_2$ share the same degree $d$, the tree with the larger root key is linked as a child of the smaller root key, producing a tree of degree $d+1$. This pairwise merging continues until all roots possess mutually distinct degrees.

---

### 2.3 Decrease-Key & Cascading Cuts

When `fib_decrease_key(heap, x, new_key)` reduces $x$'s key below its parent $y$:
1. The min-heap order between $x$ and $y$ is violated.
2. **Cut**: $x$ is severed from $y$, its parent pointer cleared, its mark cleared, and $x$ is placed into the root list.
3. **Cascading Cut**: To prevent trees from becoming overly shallow and degenerating degree bounds:
   - If parent $y$ was previously unmarked, it is marked ($\text{mark}[y] = \text{true}$), indicating it has lost one child.
   - If parent $y$ was already marked (it has now lost two children), $y$ is cut from its parent $z$ and added to the root list. The cascading cut recurses upward along the ancestral chain until an unmarked node or the root is encountered.

---

## 3. The Golden Ratio & Subtree Size Bound

Why is it termed a **Fibonacci** Heap? The name stems directly from the cascading cut rule.

### Lemma (Subtree Size Lower Bound)
Let $x$ be any node in a Fibonacci heap with degree $k = \text{degree}[x]$. Let $y_1, y_2, \dots, y_k$ denote the children of $x$ ordered by the time they were linked to $x$. When $y_i$ was linked, $x$ already had at least $i-1$ children, so $\text{degree}[y_i] \ge i-1$. Because $y_i$ can lose at most one child before being severed, $\text{degree}[y_i] \ge \max(0, i-2)$.

Let $S_k$ denote the minimum possible size of a subtree rooted at a node of degree $k$:
$$S_0 = 1, \quad S_1 = 2$$
$$S_k \ge 1 + \sum_{i=1}^k S_{\max(0, i-2)} = 2 + \sum_{j=0}^{k-2} S_j$$
By induction, this sequence satisfies:
$$S_k \ge F_{k+2}$$
where $F_n$ is the $n$-th Fibonacci number ($F_0=0, F_1=1, F_2=1, F_3=2, F_4=3, F_5=5, \dots$).

Using Binet's formula with the golden ratio $\phi = \frac{1 + \sqrt{5}}{2} \approx 1.618$:
$$F_{k+2} \ge \phi^k \implies n \ge \phi^k \implies k \le \log_\phi n$$
Hence, the maximum degree $D(n)$ of any node is strictly bounded by:
$$D(n) \le \lfloor \log_\phi n \rfloor = O(\log n)$$
For $n = 10^9$, $D(n) \le \lfloor \log_{1.618} 10^9 \rfloor \approx 43$, ensuring degree consolidation fits in a tiny 64-element register array.

---

## 4. Potential Function Amortized Analysis

Define the potential function $\Phi(H)$ for a Fibonacci heap collection $H$:
$$\Phi(H) = t(H) + 2 m(H)$$
where $t(H)$ is the number of trees in the root list and $m(H)$ is the number of marked nodes.

1. **`fib_insert`**:
   - Actual cost: $O(1)$ (append to root list).
   - $\Delta \Phi = (t + 1) - t + 2(m - m) = +1$.
   - Amortized cost: $\hat{c} = c + \Delta \Phi = O(1) + 1 = \mathbf{O(1)}$.
2. **`fib_decrease_key` with $c$ cascading cuts**:
   - Actual cost: $O(c)$ (severing $c$ nodes).
   - Number of trees increases by $c$: $\Delta t = c$.
   - The first cut nodes were marked and become unmarked roots; at most one ancestor becomes marked: $\Delta m \le - (c - 1) + 1 = 2 - c$.
   - $\Delta \Phi = \Delta t + 2 \Delta m \le c + 2(2 - c) = 4 - c$.
   - Amortized cost: $\hat{c} \le O(c) + 4 - c = \mathbf{O(1)}$.
3. **`fib_extract_min`**:
   - Actual cost: $O(D(n) + t(H))$.
   - After consolidation, the number of root trees is at most $D(n) + 1$.
   - $\Delta \Phi \le (D(n) + 1) - t(H)$.
   - Amortized cost: $\hat{c} = O(D(n) + t(H)) + (D(n) + 1 - t(H)) = \mathbf{O(D(n))} = \mathbf{O(\log n)}$.

---

## 5. Complete Implementation in Lateralus

```lateralus
// stdlib/fibonacci_heap.ltl
pub fn fib_create() -> dict {
    let mut heap = {}
    heap["min_node"] = 0
    heap["count"] = 0

    let mut keys = [0]
    let mut values = [0]
    let mut parent = [0]
    let mut child = [0]
    let mut left = [0]
    let mut right = [0]
    let mut degree = [0]
    let mut mark = [false]

    heap["keys"] = keys
    heap["values"] = values
    heap["parent"] = parent
    heap["child"] = child
    heap["left"] = left
    heap["right"] = right
    heap["degree"] = degree
    heap["mark"] = mark
    return heap
}

pub fn fib_insert(heap: dict, key: int, val: int) -> int {
    let mut keys = heap["keys"]
    let mut values = heap["values"]
    let mut parent = heap["parent"]
    let mut child = heap["child"]
    let mut left = heap["left"]
    let mut right = heap["right"]
    let mut degree = heap["degree"]
    let mut mark = heap["mark"]

    let u = keys.len()
    keys.push(key)
    values.push(val)
    parent.push(0)
    child.push(0)
    left.push(u)
    right.push(u)
    degree.push(0)
    mark.push(false)

    let min_node = heap["min_node"]
    if min_node == 0 {
        heap["min_node"] = u
    } else {
        let r = right[min_node]
        right[min_node] = u
        left[u] = min_node
        right[u] = r
        left[r] = u

        if key < keys[min_node] {
            heap["min_node"] = u
        }
    }

    let count = heap["count"]
    heap["count"] = count + 1
    return u
}

pub fn fib_link_nodes(heap: dict, y: int, x: int) {
    let mut parent = heap["parent"]
    let mut child = heap["child"]
    let mut left = heap["left"]
    let mut right = heap["right"]
    let mut degree = heap["degree"]
    let mut mark = heap["mark"]

    let y_l = left[y]
    let y_r = right[y]
    right[y_l] = y_r
    left[y_r] = y_l

    parent[y] = x
    let c = child[x]
    if c == 0 {
        child[x] = y
        left[y] = y
        right[y] = y
    } else {
        let c_r = right[c]
        right[c] = y
        left[y] = c
        right[y] = c_r
        left[c_r] = y
    }

    let d = degree[x]
    degree[x] = d + 1
    mark[y] = false
}

pub fn fib_consolidate(heap: dict) {
    let min_node = heap["min_node"]
    if min_node == 0 {
        return
    }

    let keys = heap["keys"]
    let mut left = heap["left"]
    let mut right = heap["right"]
    let degree = heap["degree"]

    let mut root_nodes = []
    let mut curr = min_node
    let mut done = false
    while not done {
        root_nodes.push(curr)
        curr = right[curr]
        if curr == min_node {
            done = true
        }
    }

    let mut a = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    let mut i = 0
    let n_roots = root_nodes.len()
    while i < n_roots {
        let mut x = root_nodes[i]
        let mut d = degree[x]

        while a[d] != 0 {
            let mut y = a[d]
            if keys[x] > keys[y] {
                let temp = x
                x = y
                y = temp
            }
            fib_link_nodes(heap, y, x)
            a[d] = 0
            d = d + 1
        }
        a[d] = x
        i = i + 1
    }

    heap["min_node"] = 0
    let mut new_min = 0

    let mut j = 0
    while j < 32 {
        let node_id = a[j]
        if node_id != 0 {
            if new_min == 0 {
                new_min = node_id
                left[node_id] = node_id
                right[node_id] = node_id
            } else {
                let r = right[new_min]
                right[new_min] = node_id
                left[node_id] = new_min
                right[node_id] = r
                left[r] = node_id

                if keys[node_id] < keys[new_min] {
                    new_min = node_id
                }
            }
        }
        j = j + 1
    }

    heap["min_node"] = new_min
}

pub fn fib_extract_min(heap: dict) -> dict {
    let mut res = {}
    res["key"] = -1
    res["val"] = -1

    let z = heap["min_node"]
    if z == 0 {
        return res
    }

    let keys = heap["keys"]
    let values = heap["values"]
    let mut parent = heap["parent"]
    let mut child = heap["child"]
    let mut left = heap["left"]
    let mut right = heap["right"]

    res["key"] = keys[z]
    res["val"] = values[z]

    let c = child[z]
    if c != 0 {
        let mut child_nodes = []
        let mut curr = c
        let mut done = false
        while not done {
            child_nodes.push(curr)
            curr = right[curr]
            if curr == c {
                done = true
            }
        }

        let mut i = 0
        let n_children = child_nodes.len()
        while i < n_children {
            let ch = child_nodes[i]
            parent[ch] = 0

            let r = right[z]
            right[z] = ch
            left[ch] = z
            right[ch] = r
            left[r] = ch

            i = i + 1
        }
    }

    let z_l = left[z]
    let z_r = right[z]
    right[z_l] = z_r
    left[z_r] = z_l

    if z_r == z {
        heap["min_node"] = 0
    } else {
        heap["min_node"] = z_r
        fib_consolidate(heap)
    }

    let count = heap["count"]
    heap["count"] = count - 1
    return res
}

pub fn fib_cut(heap: dict, x: int, y: int) {
    let mut child = heap["child"]
    let mut left = heap["left"]
    let mut right = heap["right"]
    let mut parent = heap["parent"]
    let mut degree = heap["degree"]
    let mut mark = heap["mark"]

    let x_l = left[x]
    let x_r = right[x]
    right[x_l] = x_r
    left[x_r] = x_l

    if child[y] == x {
        if x_r == x {
            child[y] = 0
        } else {
            child[y] = x_r
        }
    }

    let d = degree[y]
    degree[y] = d - 1

    let min_node = heap["min_node"]
    let r = right[min_node]
    right[min_node] = x
    left[x] = min_node
    right[x] = r
    left[r] = x

    parent[x] = 0
    mark[x] = false
}

pub fn fib_cascading_cut(heap: dict, y: int) {
    let parent = heap["parent"]
    let mut mark = heap["mark"]
    let z = parent[y]

    if z != 0 {
        if not mark[y] {
            mark[y] = true
        } else {
            fib_cut(heap, y, z)
            fib_cascading_cut(heap, z)
        }
    }
}

pub fn fib_decrease_key(heap: dict, x: int, new_key: int) -> bool {
    let mut keys = heap["keys"]
    let parent = heap["parent"]

    if new_key > keys[x] {
        return false
    }

    keys[x] = new_key
    let y = parent[x]

    if y != 0 and keys[x] < keys[y] {
        fib_cut(heap, x, y)
        fib_cascading_cut(heap, y)
    }

    let min_node = heap["min_node"]
    if keys[x] < keys[min_node] {
        heap["min_node"] = x
    }
    return true
}
```

---

## 6. Asymptotic Complexity Comparison Matrix

| Operation | Binary Heap | Binomial Heap | Pairing Heap | Fibonacci Heap |
| :--- | :--- | :--- | :--- | :--- |
| **`insert`** | $O(\log n)$ | $O(1)$ amortized | $O(1)$ | $\mathbf{O(1)}$ **amortized** |
| **`find_min`** | $O(1)$ | $O(1)$ | $O(1)$ | $\mathbf{O(1)}$ |
| **`extract_min`** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ amortized | $\mathbf{O(\log n)}$ **amortized** |
| **`decrease_key`** | $O(\log n)$ | $O(\log n)$ | $o(\log n)$ amortized | $\mathbf{O(1)}$ **amortized** |
| **`meld`** | $O(n)$ | $O(\log n)$ | $O(1)$ | $\mathbf{O(1)}$ |
| **Dijkstra SSSP** | $O((V+E)\log V)$ | $O(E \log V)$ | $O(E + V \log V)$ empirical | $\mathbf{O(E + V \log V)}$ **proven** |

---

## 7. Conclusion

By delaying balance operations until extraction and constraining tree degradation through cascading cuts, the Fibonacci Heap achieves the theoretical optimal asymptotic bound for priority queues. Its $O(1)$ amortized `decrease_key` establishes it as the mathematical pinnacle of shortest-path and spanning-tree algorithms.
