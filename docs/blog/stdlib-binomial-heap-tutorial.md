# Binomial Heap & Binary-Isomorphic Priority Queues in Lateralus

## 1. Introduction & Executive Summary

Priority queues are ubiquitous in operating systems, task schedulers, network routing, and discrete-event simulators. While binary heaps provide efficient $O(\log n)$ insertion and extraction, they suffer from a fatal structural rigidity: **merging two independent binary heaps requires $O(n)$ time**, forcing distributed systems to discard intermediate queue structures and rebuild from scratch.

In 1978, **Jean Vuillemin** introduced the **Binomial Heap**, later refined by Mark R. Brown. A binomial heap is a meldable priority queue whose underlying structure is **strictly isomorphic to binary arithmetic**. Just as any positive integer $n$ has a unique binary representation as a sum of powers of 2, a binomial heap of size $n$ consists of a collection of unique min-heap-ordered **Binomial Trees** $B_k$, where each tree $B_k$ contains exactly $2^k$ nodes.

Merging two binomial heaps mirrors the operation of a **hardware ripple-carry binary adder**: combining two trees of degree $k$ produces a carry tree of degree $k+1$ in $O(1)$ time, guaranteeing that two arbitrary heaps are melded in worst-case **$O(\log n)$** time.

This tutorial provides complete combinatorial proofs of binomial tree invariants and delivers a verified production implementation in Lateralus.

---

## 2. Mathematical Foundations: The Binomial Tree $B_k$

### 2.1 Recursive Definition
A **Binomial Tree of order $k$** (denoted $B_k$) is an ordered tree defined inductively:
- $B_0$ consists of a single node.
- For $k \ge 1$, $B_k$ is formed by linking two copies of $B_{k-1}$, placing one as the leftmost child of the root of the other.

```
  B_0       B_1          B_2               B_3
   o         o            o                 o
             |          /   \            /  |  \
             o         o     o          o   o   o
                       |               / \  |
                       o              o   o o
                                      |
                                      o
```

---

### 2.2 Structural Invariants & The Binomial Coefficient Theorem

For any binomial tree $B_k$:
1. **Total Node Count**: $|B_k| = 2^k$.
   - *Proof*: By induction, $|B_0| = 1 = 2^0$. For $k \ge 1$, $|B_k| = 2 \cdot |B_{k-1}| = 2 \cdot 2^{k-1} = 2^k$.
2. **Height**: The height of $B_k$ is exactly $k$.
3. **Root Degree**: The degree of the root is $k$, and its children are roots of binomial trees $B_{k-1}, B_{k-2}, \dots, B_0$ in decreasing order of degree.
4. **Depth Distribution (Binomial Coefficients)**:
   $$\text{Number of nodes at depth } d \text{ in } B_k = \binom{k}{d}$$
   - *Proof*: When $B_k$ is constructed from two $B_{k-1}$ trees, the root of the attached tree is placed at depth 1. By induction, the number of nodes at depth $d$ is:
     $$\binom{k-1}{d} + \binom{k-1}{d-1} = \binom{k}{d} \quad \text{(Pascal's Identity)}$$
   Summing over all depths recovers the Binomial Expansion:
   $$\sum_{d=0}^k \binom{k}{d} = (1 + 1)^k = 2^k$$

---

## 3. The Binary Isomorphism Paradigm

Consider a heap containing $n = 13$ elements. Writing 13 in binary:
$$13 = 1 \cdot 2^3 + 1 \cdot 2^2 + 0 \cdot 2^1 + 1 \cdot 2^0 = (1101)_2$$
The binomial heap contains exactly:
- One tree $B_3$ ($8$ nodes)
- One tree $B_2$ ($4$ nodes)
- Zero trees $B_1$
- One tree $B_0$ ($1$ node)
$$\text{Total nodes} = 8 + 4 + 1 = 13$$

Because each degree $k \le \lfloor \log_2 n \rfloor$ appears at most once, a binomial heap of size $n$ contains at most $\lfloor \log_2 n \rfloor + 1 = O(\log n)$ roots.

### The Ripple-Carry Adder Analogy
When two heaps $H_1$ and $H_2$ are melded:
1. Merge the root lists into a single list sorted by degree.
2. Scan through the list maintaining a `carry` when two adjacent trees have identical degree $k$. Linking them yields a tree of degree $k+1$.
3. Total time is proportional to the number of bits in $n_1 + n_2$, which is strictly $O(\log n)$.

---

## 4. Lateralus Implementation

```lateralus
// stdlib/binomial_heap.ltl
pub fn bin_create() -> dict {
    let mut heap = {}
    heap["head"] = 0
    heap["count"] = 0

    let mut keys = [0]
    let mut values = [0]
    let mut parent = [0]
    let mut child = [0]
    let mut sibling = [0]
    let mut degree = [0]

    heap["keys"] = keys
    heap["values"] = values
    heap["parent"] = parent
    heap["child"] = child
    heap["sibling"] = sibling
    heap["degree"] = degree
    return heap
}

pub fn bin_link(heap: dict, y: int, z: int) {
    let mut parent = heap["parent"]
    let mut child = heap["child"]
    let mut sibling = heap["sibling"]
    let mut degree = heap["degree"]

    parent[y] = z
    sibling[y] = child[z]
    child[z] = y
    let d = degree[z]
    degree[z] = d + 1
}

pub fn bin_merge_roots(heap: dict, h1: int, h2: int) -> int {
    if h1 == 0 { return h2 }
    if h2 == 0 { return h1 }

    let degree = heap["degree"]
    let mut sibling = heap["sibling"]

    let mut p1 = h1
    let mut p2 = h2
    let mut head = 0
    let mut tail = 0

    if degree[p1] <= degree[p2] {
        head = p1
        tail = p1
        p1 = sibling[p1]
    } else {
        head = p2
        tail = p2
        p2 = sibling[p2]
    }

    while p1 != 0 and p2 != 0 {
        if degree[p1] <= degree[p2] {
            sibling[tail] = p1
            tail = p1
            p1 = sibling[p1]
        } else {
            sibling[tail] = p2
            tail = p2
            p2 = sibling[p2]
        }
    }

    if p1 != 0 {
        sibling[tail] = p1
    } else {
        sibling[tail] = p2
    }
    return head
}

pub fn bin_meld(heap: dict, h1: int, h2: int) -> int {
    let mut new_head = bin_merge_roots(heap, h1, h2)
    if new_head == 0 { return 0 }

    let degree = heap["degree"]
    let keys = heap["keys"]
    let mut sibling = heap["sibling"]

    let mut prev = 0
    let mut curr = new_head
    let mut next = sibling[curr]

    while next != 0 {
        let mut condition = false
        if degree[curr] != degree[next] {
            condition = true
        } else {
            let next_next = sibling[next]
            if next_next != 0 and degree[next_next] == degree[curr] {
                condition = true
            }
        }

        if condition {
            prev = curr
            curr = next
        } else {
            if keys[curr] <= keys[next] {
                sibling[curr] = sibling[next]
                bin_link(heap, next, curr)
            } else {
                if prev == 0 {
                    new_head = next
                } else {
                    sibling[prev] = next
                }
                bin_link(heap, curr, next)
                curr = next
            }
        }
        next = sibling[curr]
    }
    return new_head
}

pub fn bin_insert(heap: dict, key: int, val: int) -> int {
    let mut keys = heap["keys"]
    let mut values = heap["values"]
    let mut parent = heap["parent"]
    let mut child = heap["child"]
    let mut sibling = heap["sibling"]
    let mut degree = heap["degree"]

    let u = keys.len()
    keys.push(key)
    values.push(val)
    parent.push(0)
    child.push(0)
    sibling.push(0)
    degree.push(0)

    let head = heap["head"]
    let new_head = bin_meld(heap, head, u)
    heap["head"] = new_head

    let count = heap["count"]
    heap["count"] = count + 1
    return u
}

pub fn bin_extract_min(heap: dict) -> dict {
    let mut res = {}
    res["key"] = -1
    res["val"] = -1

    let head = heap["head"]
    if head == 0 { return res }

    let keys = heap["keys"]
    let values = heap["values"]
    let mut parent = heap["parent"]
    let child = heap["child"]
    let mut sibling = heap["sibling"]

    let mut min_node = head
    let mut min_prev = 0
    let mut prev = head
    let mut curr = sibling[head]

    while curr != 0 {
        if keys[curr] < keys[min_node] {
            min_node = curr
            min_prev = prev
        }
        prev = curr
        curr = sibling[curr]
    }

    res["key"] = keys[min_node]
    res["val"] = values[min_node]

    if min_prev == 0 {
        heap["head"] = sibling[min_node]
    } else {
        sibling[min_prev] = sibling[min_node]
    }

    let mut child_curr = child[min_node]
    let mut reversed_head = 0

    while child_curr != 0 {
        let next_child = sibling[child_curr]
        parent[child_curr] = 0
        sibling[child_curr] = reversed_head
        reversed_head = child_curr
        child_curr = next_child
    }

    let current_head = heap["head"]
    let new_head = bin_meld(heap, current_head, reversed_head)
    heap["head"] = new_head

    let count = heap["count"]
    heap["count"] = count - 1
    return res
}

pub fn bin_decrease_key(heap: dict, x: int, new_key: int) -> bool {
    let mut keys = heap["keys"]
    let mut values = heap["values"]
    let parent = heap["parent"]

    if new_key > keys[x] { return false }

    keys[x] = new_key
    let mut curr = x
    let mut p = parent[curr]

    while p != 0 and keys[curr] < keys[p] {
        let temp_k = keys[curr]
        keys[curr] = keys[p]
        keys[p] = temp_k

        let temp_v = values[curr]
        values[curr] = values[p]
        values[p] = temp_v

        curr = p
        p = parent[curr]
    }
    return true
}
```

---

## 5. Asymptotic Complexity Comparison Matrix

| Operation | Binary Heap | Binomial Heap | Fibonacci Heap |
| :--- | :--- | :--- | :--- |
| **`insert`** | $O(\log n)$ | $O(1)$ amortized / $O(\log n)$ worst-case | $O(1)$ amortized |
| **`find_min`** | $O(1)$ | $O(\log n)$ (or $O(1)$ with pointer) | $O(1)$ |
| **`extract_min`** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ amortized |
| **`decrease_key`** | $O(\log n)$ | $O(\log n)$ | $O(1)$ amortized |
| **`meld`** | $O(n)$ | $\mathbf{O(\log n)}$ **worst-case** | $O(1)$ amortized |

---

## 6. Conclusion

The Binomial Heap illustrates the profound connection between combinatorial tree structures and positional numeral systems. By modeling priority queue unions directly on binary addition, it provides a deterministic, worst-case $O(\log n)$ merge guarantee that laid the theoretical foundation for Fibonacci and Pairing Heaps.
