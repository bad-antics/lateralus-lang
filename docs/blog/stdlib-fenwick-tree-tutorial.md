# Standard Library Deep Dive: Fenwick Tree (Binary Indexed Tree / BIT)

The **Fenwick Tree** (also known as the **Binary Indexed Tree / BIT**), introduced by Peter M. Fenwick in 1994, is an exceptionally compact and elegant data structure designed to resolve the dynamic prefix sum dilemma.

In dynamic arrays subject to ongoing modifications:
- **Naive Array**: $O(1)$ point update, but $O(n)$ prefix sum query.
- **Prefix Sum Array**: $O(1)$ prefix sum query, but $O(n)$ point update.

The Fenwick Tree strikes an optimal balance: both **point update** and **prefix sum query** execute in deterministic **$O(\log n)$** time while requiring strictly **$O(n)$** auxiliary storage (exactly $n + 1$ elements) without any pointer overhead or recursion.

---

## 1. Algorithmic Architecture & The Lowbit Decomposition

Every positive integer $i$ can be uniquely expressed as a sum of powers of two according to its binary representation. The fundamental operator powering the Fenwick tree is **lowbit**:

$$\text{lowbit}(i) = 2^k$$

where $k$ is the position of the least significant set bit (1-bit) in $i$. For example:
- $\text{lowbit}(6) = \text{lowbit}(110_2) = 2$
- $\text{lowbit}(12) = \text{lowbit}(1100_2) = 4$
- $\text{lowbit}(16) = \text{lowbit}(10000_2) = 16$

### Tree Responsibility Range
In a 1-indexed Fenwick tree $T$, each index $i$ stores the sum of elements in the half-open interval:

$$T[i] = \sum_{j = i - \text{lowbit}(i) + 1}^{i} A[j]$$

```
Index  Binary   lowbit  Maintained Interval
-------------------------------------------
 1     0001_2     1     [1, 1]
 2     0010_2     2     [1, 2]
 3     0011_2     1     [3, 3]
 4     0100_2     4     [1, 4]
 5     0101_2     1     [5, 5]
 6     0110_2     2     [5, 6]
 7     0111_2     1     [7, 7]
 8     1000_2     8     [1, 8]
```

---

## 2. Core Operation Mechanics

### 2.1 Prefix Sum Query (`fenwick_query`)
To calculate $\sum_{j=1}^{i} A[j]$, decompose index $i$ by repeatedly subtracting its least significant 1-bit:

$$i \leftarrow i - \text{lowbit}(i)$$

Each step adds $T[i]$ to the cumulative sum until $i = 0$. Since an integer $\le n$ has at most $\lfloor \log_2 n \rfloor + 1$ set bits, this loop executes in guaranteed $O(\log n)$ steps.

### 2.2 Point Delta Update (`fenwick_add`)
When element $A[i]$ changes by $+\Delta$, all Fenwick tree nodes whose responsibility interval contains $i$ must be adjusted. The indices of these ancestor nodes are obtained by repeatedly adding the least significant bit:

$$i \leftarrow i + \text{lowbit}(i)$$

until $i > n$. This climb also terminates in at most $O(\log n)$ iterations.

### 2.3 Arbitrary Range Query (`fenwick_range_query`)
By standard prefix subtraction:

$$\sum_{j=L}^{R} A[j] = \text{Query}(R) - \text{Query}(L - 1)$$

---

## 3. Lateralus Reference Implementation

```lateralus
fn lowbit(x) {
    let p = 1
    while p <= x {
        if (x / p) % 2 != 0 {
            return p
        }
        p = p * 2
    }
    return 1
}

pub fn create_fenwick_tree(n) {
    let ft = dict()
    ft["n"] = n
    let arr = []
    let i = 0
    while i <= n {
        arr = push(arr, 0)
        i = i + 1
    }
    ft["tree"] = arr
    return ft
}

pub fn fenwick_add(ft, idx, delta) {
    let n = ft["n"]
    let arr = ft["tree"]
    let i = idx
    while i <= n {
        arr[i] = arr[i] + delta
        i = i + lowbit(i)
    }
    ft["tree"] = arr
}

pub fn fenwick_query(ft, idx) {
    let arr = ft["tree"]
    let sum = 0
    let i = idx
    while i > 0 {
        sum = sum + arr[i]
        i = i - lowbit(i)
    }
    return sum
}

pub fn fenwick_range_query(ft, left, right) {
    if left > right {
        return 0
    }
    if left <= 1 {
        return fenwick_query(ft, right)
    }
    return fenwick_query(ft, right) - fenwick_query(ft, left - 1)
}
```

---

## 4. Comparison: Fenwick Tree vs. Segment Tree

| Feature | Fenwick Tree (BIT) | Segment Tree |
| :--- | :---: | :---: |
| **Point Update** | $O(\log n)$ | $O(\log n)$ |
| **Range Sum Query** | $O(\log n)$ | $O(\log n)$ |
| **Space Overhead** | **$n + 1$ (Optimal)** | $4n$ |
| **Code Footprint** | ~15 lines (Minimal) | 60+ lines |
| **Cache Locality** | Sequential flat array | Branching tree hops |
| **Runtime Constant** | Extremely small (3-5x faster) | Moderate (recursion/pointers) |

---

## 5. Industrial Applications

1. **High-Frequency Trading (HFT) Order Book Depth**:
   Instantly computing cumulative bid/ask volume up to specified price levels for slippage prediction and limit-order matching.
2. **Real-Time Telemetry & Rolling Percentiles**:
   Maintaining dynamic histogram counts across metrics to calculate arbitrary rank percentiles in $O(\log n)$.
3. **Inversion Count & Ranking Permutations**:
   Efficiently detecting sortedness divergence and bubble-sort inversion counts in $O(n \log n)$ time.
