# Kadane's Maximum Subarray & Submatrix Algorithm in Lateralus

## 1. Introduction

The **Maximum Subarray Problem** asks: Given a sequence of $n$ numbers (which may include negative values), identify the contiguous subsegment that yields the maximum possible cumulative sum:

$$\max_{0 \le i \le j < n} \sum_{k=i}^j A[k]$$

Historically, this problem progressed through several computational milestones:
- **Brute Force**: $\mathcal{O}(n^3)$ examining every pair $(i, j)$ and summing the interval.
- **Prefix Sums**: $\mathcal{O}(n^2)$ precomputing running totals.
- **Divide and Conquer**: $\mathcal{O}(n \log n)$ proposed by Jon Bentley.
- **Kadane's Algorithm** (1984): Discovered by Joseph Born Kadane at Carnegie Mellon University, solving the problem in optimal linear time:

$$\mathcal{O}(n) \text{ time} \quad \text{and strictly} \quad \mathcal{O}(1) \text{ auxiliary space!}$$

Furthermore, by applying column prefix compression across row bounds, Kadane's 1D algorithm generalizes to solve the **2D Maximum Submatrix Sum** problem in $\mathcal{O}(R^2 \cdot C)$ time, serving as a core technique in image processing, quantitative finance, and spatial clustering.

This tutorial provides a complete walkthrough of implementing Kadane's algorithm in Lateralus (`stdlib/kadane.ltl`), along with trading streak analysis and golden test vectors.

---

## 2. Core Dynamic Programming Recurrence

### 2.1 Bellman Optimality Principle
Let $\text{current\_max}[i]$ represent the maximum contiguous subarray sum ending strictly at index $i$. For element $A[i]$, we face a binary choice:
1. Start a new subarray beginning at $A[i]$ (cost: $A[i]$).
2. Extend the existing optimal subarray ending at $i-1$ (cost: $\text{current\_max}[i-1] + A[i]$).

$$\text{current\_max}[i] = \max(A[i], \text{current\_max}[i-1] + A[i])$$

The global maximum is simply the supreme value encountered across all terminating indices:

$$\text{max\_so\_far} = \max_{0 \le i < n} \text{current\_max}[i]$$

### 2.2 Boundary Interval Tracking
To reconstruct the exact start and end indices `[start, end]`:
- Whenever $A[i] > \text{current\_max} + A[i]$, the previous streak dragged down the cumulative total below zero; we reset `temp_start = i`.
- Whenever `current_max > max_so_far`, we update `start = temp_start` and `end = i`.
- This ensures optimal interval extraction with zero memory overhead!

### 2.3 2D Submatrix Generalization
For an $R \times C$ matrix:
1. Fix top row $r_1$ and bottom row $r_2$ ($\mathcal{O}(R^2)$ pairs).
2. Maintain a running 1D array `col_sums` where $\text{col\_sums}[c] = \sum_{r=r_1}^{r_2} M[r][c]$.
3. Apply `kadane_1d` on `col_sums` in $\mathcal{O}(C)$ time.
4. Total complexity: $\mathcal{O}(R^2 \cdot C)$.

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
pub fn kadane_1d(nums) {
    let n = len(nums)
    if n == 0 {
        let res = dict()
        res["max_sum"] = 0
        res["start"] = -1
        res["end"] = -1
        return res
    }

    let max_so_far = nums[0]
    let current_max = nums[0]
    let start_idx = 0
    let end_idx = 0
    let temp_start = 0

    let i = 1
    while i < n {
        let x = nums[i]
        if x > current_max + x {
            current_max = x
            temp_start = i
        } else {
            current_max = current_max + x
        }

        if current_max > max_so_far {
            max_so_far = current_max
            start_idx = temp_start
            end_idx = i
        }
        i = i + 1
    }

    let res = dict()
    res["max_sum"] = max_so_far
    res["start"] = start_idx
    res["end"] = end_idx
    return res
}

pub fn kadane_2d(matrix, rows, cols) {
    if rows == 0 or cols == 0 {
        let res = dict()
        res["max_sum"] = 0
        res["r1"] = -1
        res["r2"] = -1
        res["c1"] = -1
        res["c2"] = -1
        return res
    }

    let global_max = matrix[0][0]
    let best_r1 = 0
    let best_r2 = 0
    let best_c1 = 0
    let best_c2 = 0

    let r1 = 0
    while r1 < rows {
        let col_sums = []
        let c = 0
        while c < cols {
            col_sums = push(col_sums, 0)
            c = c + 1
        }

        let r2 = r1
        while r2 < rows {
            let col_idx = 0
            while col_idx < cols {
                col_sums[col_idx] = col_sums[col_idx] + matrix[r2][col_idx]
                col_idx = col_idx + 1
            }

            let sub_res = kadane_1d(col_sums)
            if sub_res["max_sum"] > global_max {
                global_max = sub_res["max_sum"]
                best_r1 = r1
                best_r2 = r2
                best_c1 = sub_res["start"]
                best_c2 = sub_res["end"]
            }
            r2 = r2 + 1
        }
        r1 = r1 + 1
    }

    let res = dict()
    res["max_sum"] = global_max
    res["r1"] = best_r1
    res["r2"] = best_r2
    res["c1"] = best_c1
    res["c2"] = best_c2
    return res
}
```

---

## 4. Real-World Engineering Applications

1. **Quantitative Algorithmic Trading**: Pinpointing optimal holding periods, peak winning execution windows, and evaluating maximum continuous returns over market regimes.
2. **Computer Vision & Thermal Saliency**: Identifying the brightest rectangular regions in grayscale or infrared sensor matrix imagery.
3. **Genomic Alignment Scoring**: Locating the highest-scoring local sequence matches between DNA/RNA sequences under match/mismatch scoring matrices.
4. **Digital Signal Processing**: Extracting peak burst power transmission intervals from noisy RF streaming sensor data.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_kadane_tutorial.ltl
python -m lateralus_lang check examples/kadane_tutorial.ltl
pytest tests/test_compiler.py
```
