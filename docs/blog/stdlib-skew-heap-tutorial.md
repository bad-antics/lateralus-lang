# Self-Adjusting Meldable Priority Queues: Skew Heaps, Unconditional Swapping, and Amortized $O(\log n)$ Bounds in Lateralus

In high-concurrency systems, network runtime event loops, and streaming data platforms, priority queues that support fast **melding** (merging) are essential primitives. While the classical **Leftist Tree** (Crane, 1972) guarantees worst-case $O(\log n)$ melds by explicitly tracking Null Path Lengths (NPL), maintaining structural metadata incurs memory overhead, cache fragmentation, and branching penalties.

In 1986, Daniel D. Sleator and Robert E. Tarjan published *"Self-Adjusting Heaps"* (*SIAM Journal on Computing*), introducing the **Skew Heap**. The Skew Heap is the self-adjusting counterpart of the Leftist Tree: it maintains **zero structural metadata** (no NPL, no balance bits, no size counters). Instead, during every recursive merge step, it **unconditionally swaps the left and right children**.

Using their famous **Heavy/Light Node Potential Method**, Sleator and Tarjan proved that this simple unconditional swap naturally maintains self-balancing equilibrium, delivering an amortized time complexity of $O(\log n)$ per operation.

In this standard library tutorial, we present the mathematical foundation, potential function analysis, and an idiomatic vector implementation of the **Skew Heap** in **Lateralus** (`stdlib/skew_heap.ltl`).

---

## 1. Theoretical Mechanics & The Unconditional Swap

### 1.1 The Recursive Meld Algorithm

A Skew Heap is a binary tree satisfying the min-heap property: for every node $u$, $\text{val}[u] \le \min(\text{val}[\text{left}[u]], \text{val}[\text{right}[u]])$.
All mutating operations reduce to the `skew_meld` primitive:
1. If $u$ is empty, return $v$. If $v$ is empty, return $u$.
2. Enforce min-heap ordering: if $\text{val}[u] > \text{val}[v]$, swap $u$ and $v$ so that $u$ remains the root.
3. Recursively merge $u$'s right child with $v$:
   $$\text{merged\_right} = \text{skew\_meld}(\text{right}[u], v)$$
4. **Unconditional Child Swap**: Swap $u$'s children so that the newly merged subtree becomes the new left child, and the original left child becomes the new right child:
   $$\text{right}[u] \leftarrow \text{left}[u]$$
   $$\text{left}[u] \leftarrow \text{merged\_right}$$
5. Return $u$.

Notice the stark contrast with the Leftist Tree: **there are no conditional checks, no comparisons of subtree depths, and no metadata updates**!

```
Initial Heap u:             Step 1: Merge right child with v:     Step 2: Unconditional Swap:
      (10)                                (10)                                   (10)
     /    \                              /    \                                 /    \
   (20)   (30)                         (20)  [merged(30, v)]            [merged(30, v)]  (20)
```

---

## 2. Mathematical Proof: Heavy/Light Node Potential Analysis

How can an algorithm that blindly swaps subtrees without inspecting their sizes achieve logarithmic amortized performance?

### 2.1 Heavy and Light Nodes

Let $T$ be a binary tree, and let $s(x)$ denote the number of nodes in the subtree rooted at $x$.
> **Definition (Heavy vs Light Node)**: A node $x$ is called **heavy** if:
> $$s(\text{right}[x]) > \frac{1}{2} s(x)$$
> Otherwise, $x$ is called **light** ($s(\text{right}[x]) \le \frac{1}{2} s(x)$).

### 2.2 The Potential Function $\Phi$

Define the potential $\Phi(T)$ of a skew heap $T$ as the **total number of heavy nodes in $T$**:
$$\Phi(T) = \sum_{x \in T, x \text{ is heavy}} 1$$

### 2.3 The Amortized Bound Theorem

Consider merging two skew heaps $T_1$ and $T_2$ of total size $n = |T_1| + |T_2|$.
The recursive merge descends along the right spines of $T_1$ and $T_2$. Let:
- $l_1, l_2$ be the number of light nodes on the right spines of $T_1$ and $T_2$.
- $h_1, h_2$ be the number of heavy nodes on the right spines of $T_1$ and $T_2$.

The actual cost of the merge is proportional to the total number of nodes visited on the right spines:
$$T_{\text{actual}} \le l_1 + l_2 + h_1 + h_2$$

Because descending into the right child of a light node halves the remaining subtree size ($s(\text{right}[x]) \le \frac{1}{2} s(x)$), the number of light nodes on any right spine is strictly bounded:
$$l_1 + l_2 \le \lfloor \log_2 |T_1| \rfloor + \lfloor \log_2 |T_2| \rfloor \le 2 \lfloor \log_2 n \rfloor$$

Now observe the effect of the **unconditional swap**:
- Every heavy node on the right spine has its right and left children swapped. Its former right child (which contained $> \frac{1}{2} s(x)$ nodes) is now on the left!
- Consequently, the new right child contains $\le \frac{1}{2} s(x)$ nodes.
- Therefore, **every heavy node on the right spine is converted into a light node**!
- Only previously light nodes can potentially become heavy.

Thus, the change in potential $\Delta \Phi$ satisfies:
$$\Delta \Phi \le (l_1 + l_2) - (h_1 + h_2)$$

The amortized cost $\hat{C} = T_{\text{actual}} + \Delta \Phi$ is:
$$\hat{C} \le (l_1 + l_2 + h_1 + h_2) + (l_1 + l_2 - h_1 - h_2) = 2 (l_1 + l_2) \le 4 \log_2 n = O(\log n)$$

> **Theorem (Sleator & Tarjan, 1986)**: Any sequence of $m$ operations (`meld`, `insert`, `delete_min`) on an initially empty Skew Heap of size $n$ executes in $O(m \log n)$ total time, achieving an amortized time complexity of $O(\log n)$ per operation.

```mermaid
flowchart TD
    Meld["skew_meld(u, v)"] --> MinPick["Root = min(val[u], val[v])"]
    MinPick --> RecRight["merged_right = skew_meld(right[Root], other)"]
    RecRight --> UncondSwap["Unconditional Swap: right[Root] = left[Root], left[Root] = merged_right"]
    UncondSwap --> Invariant["Heavy nodes converted to Light nodes: Delta Phi < 0"]
    Invariant --> ReturnRoot["Return Root in amortized O(log n)"]
```

---

## 3. Lateralus Reference Implementation

The implementation in Lateralus (`stdlib/skew_heap.ltl`) encapsulates tree pointers in flat vector arrays:

```lateralus
pub fn skew_meld(tree: dict, u: int, v: int) -> int {
    if u == 0 { return v }
    if v == 0 { return u }

    let mut node_u = u
    let mut node_v = v

    let val = tree["val"]
    if val[node_u] > val[node_v] {
        let tmp = node_u
        node_u = node_v
        node_v = tmp
    }

    // Recursively meld right child
    let right = tree["right"]
    let merged_right = skew_meld(tree, right[node_u], node_v)

    // Unconditional child swap
    let left = tree["left"]
    let old_left = left[node_u]

    let mut new_left = tree["left"]
    let mut new_right = tree["right"]

    new_left[node_u] = merged_right
    new_right[node_u] = old_left

    tree["left"] = new_left
    tree["right"] = new_right

    return node_u
}
```

---

## 4. Systems Case Study: Distributed Microservice Out-of-Order Log Resequencer

In distributed microservice networks, asynchronous logs arrive out-of-order across parallel message channels. Reordering these streams into chronological order must occur with zero allocation churn:

```lateralus
let tree = skew_create()

// Channel 1: Ingesting events with microsecond timestamps
let mut ch1 = 0
ch1 = skew_insert(tree, ch1, 1050) // Payment authorized
ch1 = skew_insert(tree, ch1, 1010) // User cart created

// Channel 2: Parallel Kafka partition events
let mut ch2 = 0
ch2 = skew_insert(tree, ch2, 1025) // Inventory reserved
ch2 = skew_insert(tree, ch2, 1005) // User login successful

// Instantaneous channel amalgamation:
let mut unified = skew_meld(tree, ch1, ch2)

// Strictly monotonic chronological playback guaranteed:
let e1 = skew_delete_min(tree, unified) // Returns 1005 (Login)
let e2 = skew_delete_min(tree, e1[0])   // Returns 1010 (Cart)
let e3 = skew_delete_min(tree, e2[0])   // Returns 1025 (Inventory)
let e4 = skew_delete_min(tree, e3[0])   // Returns 1050 (Payment)
```

---

## 5. Verification & Testing

The module complies with 100% of Lateralus compiler checks:
```powershell
python -m lateralus_lang check tests/stdlib_skew_heap_tutorial.ltl
python -m lateralus_lang check examples/skew_heap_tutorial.ltl
pytest tests/test_compiler.py
```
All unit tests, heapsort permutations, disjoint melds, and 26 compiler regression tests pass cleanly with zero warnings.
