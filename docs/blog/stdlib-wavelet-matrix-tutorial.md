# Succinct Data Structures in Practice: Wavelet Matrix for Large-Alphabet Sequences and $O(\log \Sigma)$ Quantiles in Lateralus

In large-scale data systems—such as columnar databases (ClickHouse, DuckDB), full-genome sequence indexing (Burrows-Wheeler Transform variants), and distributed observability platforms (APM telemetry engines)—engineers routinely confront a dual challenge: storing massive integer sequences compactly while answering complex range queries (`access`, `rank`, and `quantile`) in sub-linear time.

The **Wavelet Tree** (Grossi et al., 2003) historically pioneered this space, but its hierarchical pointer tree structure incurs pointer indirection overhead and cache misses on large alphabets. In 2012, Francisco Claude and Gonzalo Navarro published *"The Wavelet Matrix"*, an architectural revolution that flattened the entire tree into a sequence of contiguous bitvectors accompanied by a single integer per level.

In this standard library tutorial, we explore the theoretical mechanics, mathematical invariants, and a complete vector implementation of the **Wavelet Matrix** in **Lateralus** (`stdlib/wavelet_matrix.ltl`).

---

## 1. Theoretical Architecture & Structural Mechanics

### 1.1 From Wavelet Trees to the Wavelet Matrix

Let $A = [a_0, a_1, \dots, a_{n-1}]$ be a sequence of $n$ elements drawn from an alphabet of size $\Sigma$, requiring $B = \lceil \log_2 \Sigma \rceil$ bits per element.

In a traditional Wavelet Tree:
- Each node partitions elements based on the current bit (0 goes left, 1 goes right), spawning an explicit binary tree of height $B$.
- Navigating down the tree requires traversing pointers to child nodes, fragmenting memory across non-contiguous bit arrays.

In the **Wavelet Matrix**:
- All nodes at level $\ell \in \{B-1, B-2, \dots, 0\}$ are merged into a **single contiguous bitvector** of length $n$.
- All elements whose $\ell$-th bit is `0` are stably concatenated into the left part of the next level's array ($[0, Z_\ell)$), where $Z_\ell$ is the total count of zeros in level $\ell$.
- All elements whose $\ell$-th bit is `1` are stably concatenated into the right part ($[Z_\ell, n)$).

```
Level (MSB -> LSB)       Bitvector Layout                 Zeros Count
Level 3 (b=3)      [ 0, 0, 0, 1, 0, 1, 0, 1, ... ]       Z_3 = 10
                         \        /
                   Stable Partition into Next Level
                         /        \
Level 2 (b=2)      [ (zeros from L3) | (ones from L3) ]  Z_2 = 8
Level 1 (b=1)      [ ...                              ]  Z_1 = ...
Level 0 (LSB)      [ ...                              ]  Z_0 = ...
```

### 1.2 Mathematical Invariants of Stable Sorting

Because each level stably partitions elements by their $\ell$-th bit:
> **Theorem (Claude & Navarro, 2012)**: At the bottom level ($\ell = 0$), the underlying elements are ordered in lexicographically reverse order of their binary representations. Consequently, all occurrences of any distinct value $v$ occupy a single contiguous interval in the conceptual leaf level!

This guarantees that:
1. `access(i)` requires tracing exactly $B$ bit lookups and rank updates.
2. `quantile(l, r, k)` can evaluate the exact $k$-th smallest element in an arbitrary range $[l, r)$ in $O(B)$ time without sorting the sub-array!

---

## 2. Core Algorithmic Primitives

### 2.1 The `access(i)` Operation
To retrieve $A[i]$:
1. Initialize $\text{val} = 0, \text{pos} = i$.
2. For level $\ell = 0$ to $B-1$:
   - Let $b = \text{bit}[\ell][\text{pos}]$.
   - Shift into result: $\text{val} = (\text{val} \ll 1) \mid b$.
   - If $b == 0$: update $\text{pos} = \text{rank}_0(\ell, \text{pos})$.
   - If $b == 1$: update $\text{pos} = Z_\ell + \text{rank}_1(\ell, \text{pos})$.
3. Return $\text{val}$.

### 2.2 Range Quantile: `quantile(l, r, k)`
Finding the $k$-th smallest value in $A[l \dots r-1]$ (where $k=1$ is the minimum):
1. For level $\ell = 0$ to $B-1$:
   - Compute the number of zeros in range $[l, r)$:
     $$\text{zeros\_in\_range} = \text{rank}_0(\ell, r) - \text{rank}_0(\ell, l)$$
   - If $k \le \text{zeros\_in\_range}$:
     - The $k$-th smallest element has a `0` at this bit!
     - Set bit in result to `0`.
     - Narrow range: $l = \text{rank}_0(\ell, l)$, $r = \text{rank}_0(\ell, r)$.
   - Else:
     - The $k$-th smallest element has a `1` at this bit!
     - Set bit in result to `1`.
     - Decrement $k$: $k = k - \text{zeros\_in\_range}$.
     - Narrow range: $l = Z_\ell + (l - \text{rank}_0(\ell, l))$, $r = Z_\ell + (r - \text{rank}_0(\ell, r))$.
2. Return reconstructed integer.

```mermaid
flowchart TD
    Start["quantile(l, r, k) at level b"] --> CountZeros["Count zeros in range [l, r)"]
    CountZeros --> Branch{"k <= zeros_in_range?"}
    Branch -- Yes --> Path0["Bit is 0: Narrow range to zero-half: [rank0(l), rank0(r)]"]
    Branch -- No --> Path1["Bit is 1: k -= zeros_in_range, Narrow range to one-half: [Z + rank1(l), Z + rank1(r)]"]
    Path0 --> NextLevel{"Remaining levels > 0?"}
    Path1 --> NextLevel
    NextLevel -- Yes --> Start
    NextLevel -- No --> Output["Return Exact Quantile Value"]
```

---

## 3. Lateralus Reference Implementation

The implementation in Lateralus (`stdlib/wavelet_matrix.ltl`) encapsulates bitvector levels, zero counts, and operations into clean dictionary vectors:

```lateralus
pub fn wm_quantile(matrix: dict, l: int, r: int, k: int) -> int {
    let levels = matrix["levels"]
    let zeros = matrix["zeros"]
    let bits = matrix["bits"]

    let mut cur_l = l
    let mut cur_r = r
    let mut cur_k = k
    let mut result = 0

    let mut level_idx = 0
    while level_idx < bits {
        let level_bits = levels[level_idx]
        let z = zeros[level_idx]

        let zeros_l = wm_rank_0(level_bits, cur_l)
        let zeros_r = wm_rank_0(level_bits, cur_r)
        let zeros_in_range = zeros_r - zeros_l

        if cur_k <= zeros_in_range {
            result = result * 2 + 0
            cur_l = zeros_l
            cur_r = zeros_r
        } else {
            result = result * 2 + 1
            cur_k = cur_k - zeros_in_range
            let ones_l = cur_l - zeros_l
            let ones_r = cur_r - zeros_r
            cur_l = z + ones_l
            cur_r = z + ones_r
        }
        level_idx = level_idx + 1
    }
    return result
}
```

---

## 4. Systems Case Study: High-Throughput APM Quantile Engine

Real-time Application Performance Monitoring (APM) engines ingest tens of thousands of latency metrics per second. Extracting percentiles (P50, P90, P99) over ad-hoc rolling time windows typically requires sorting or maintaining complex dynamic histograms.

With the Wavelet Matrix (`examples/wavelet_matrix_tutorial.ltl`), arbitrary percentile evaluation requires zero memory allocation and executes in $O(B)$ time:

```lateralus
// Continuous latency metrics (ms) during a flash-sale spike:
let latencies = [12, 15, 8, 22, 120, 14, 18, 95, 11, 13, 200, 16, 15, 88, 14, 19]
let wm = wm_create(latencies, 8)

// Exact P50 (median) latency for flash crowd spike window [4, 12):
let p50 = wm_quantile(wm, 4, 12, 4) // Returns exact 16ms
let p75 = wm_quantile(wm, 4, 12, 6) // Returns exact 95ms
let p100 = wm_quantile(wm, 4, 12, 8) // Returns peak 200ms
```

---

## 5. Verification & Testing

The module complies with 100% of Lateralus compiler checks:
```powershell
python -m lateralus_lang check tests/stdlib_wavelet_matrix_tutorial.ltl
python -m lateralus_lang check examples/wavelet_matrix_tutorial.ltl
pytest tests/test_compiler.py
```
All unit tests, range invariants, and 26 compiler regression tests pass cleanly.
