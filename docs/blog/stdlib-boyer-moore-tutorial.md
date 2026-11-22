# Standard Library Deep Dive: Boyer-Moore Fast String Search Algorithm

The **Boyer-Moore string-search algorithm**, published by Robert S. Boyer and J Strother Moore in 1977, is widely recognized as the benchmark of practical single-pattern string searching.

While classical algorithms like Knuth-Morris-Pratt (KMP) examine text strictly left-to-right in $O(n)$ linear time, Boyer-Moore adopts a revolutionary counter-intuitive insight: **match characters from right to left starting at the end of the pattern**. By combining this with the **Bad Character Heuristic**, the algorithm frequently skips large blocks of text without reading them, achieving a remarkable **sublinear average time complexity of $O(n / m)$**.

---

## 1. Algorithmic Architecture: Right-to-Left Scanning

Given a text $T$ of length $n$ and pattern $P$ of length $m$:
Align $P$ with the beginning of $T$ at shift $s = 0$. Compare characters starting from $j = m - 1$ down to $0$:

```
Text:     . . . A B C D . . .
Pattern:        A B C D
                <--- (Scan right-to-left from 'D' to 'A')
```

If a mismatch occurs at text character $c = T[s + j]$ and pattern character $P[j]$, $c$ is designated the **Bad Character**.

---

## 2. The Bad Character Heuristic

Let $last(c)$ denote the rightmost index where character $c$ appears in pattern $P$ ($0 \le last(c) < m$):

1. **Case 1: Bad character occurs in $P$ ($last(c) < j$)**:
   Shift the pattern to the right by:
   $$\text{shift} = j - last(c)$$
   This aligns the rightmost occurrence of $c$ in the pattern directly under the bad character in the text.

2. **Case 2: Bad character does not occur in $P$ ($last(c) = -1$)**:
   Shift the pattern completely past the bad character:
   $$\text{shift} = j - (-1) = j + 1$$
   When the mismatch happens at the very end ($j = m - 1$), the pattern jumps forward by the entire length $m$ in a single step!

```
Shift Calculation:
Text:      . . . X . . .
Pattern:   A B C D
               ^ (Mismatch at 'D', bad char 'X' not in pattern)
New Shift: ------> Pattern jumps forward by 4 full characters!
```

---

## 3. Lateralus Reference Implementation

```lateralus
fn find_last_occurrence(pattern, m, ch) {
    let i = m - 1
    while i >= 0 {
        if pattern[i] == ch {
            return i
        }
        i = i - 1
    }
    return -1
}

pub fn boyer_moore_search(text, pattern) {
    let n = len(text)
    let m = len(pattern)
    if m == 0 or n < m {
        return -1
    }

    let s = 0
    while s <= (n - m) {
        let j = m - 1

        while j >= 0 and pattern[j] == text[s + j] {
            j = j - 1
        }

        if j < 0 {
            return s
        } else {
            let bad_ch = text[s + j]
            let last_idx = find_last_occurrence(pattern, m, bad_ch)
            let shift = j - last_idx
            if shift < 1 {
                shift = 1
            }
            s = s + shift
        }
    }

    return -1
}
```

---

## 4. Complexity & Performance Analysis

| Algorithm | Worst-Case Time | Average-Case Time | Text Character Inspections |
| :--- | :---: | :---: | :---: |
| **Naive Scan** | $O(n \cdot m)$ | $O(n)$ | $\approx n$ |
| **KMP** | $O(n + m)$ | $O(n)$ | $\approx n$ |
| **Boyer-Moore** | $O(n \cdot m)$ | **$O(n / m)$ Sublinear** | **Much less than $n$** |

*(As pattern length $m$ increases, Boyer-Moore inspects progressively fewer characters, running faster rather than slower).*

---

## 5. Industrial Applications

1. **GNU `grep` and Modern Fast Grep (ripgrep)**:
   Serves as the primary fast-path algorithm for fixed string and literal searches.
2. **Text Editor Find / Replace Engines (VS Code / Sublime Text)**:
   Enables instant Ctrl+F search responsiveness across megabytes of open source code without noticeable CPU spikes.
3. **High-Throughput Log Aggregators**:
   Rapidly filtering gigabytes of JSON log messages for error keywords (`FATAL`, `EXCEPTION`).
