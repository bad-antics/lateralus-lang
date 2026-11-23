# Standard Library Deep Dive: Suffix Array (SA) & Substring Binary Search

The **Suffix Array (SA)**, invented by Udi Manber and Gene Myers in 1990, is a space-efficient data structure for string processing and full-text pattern matching.

While Suffix Trees solve exact substring queries in $O(m)$ time, their pointer-heavy node representations consume 10x to 20x the size of the original text, rendering them impractical for whole-genome indexing or multi-gigabyte corpora. The Suffix Array achieves near-identical capabilities using only a flat integer array of size $n$, cutting memory consumption by over 80% while enabling guaranteed **$O(m \log n)$** binary search queries.

---

## 1. Formal Definition & The Classic Permutation

Given a text $S$ of length $n$, the $i$-th suffix is the substring $S[i \dots n-1]$ starting at index $i$ and continuing to the end.

The **Suffix Array** $sa$ is an array of integers in the range $[0, n-1]$ representing the starting positions of all suffixes of $S$ sorted in strictly ascending lexicographical order:

$$\text{Suffix}(sa[0]) < \text{Suffix}(sa[1]) < \dots < \text{Suffix}(sa[n-1])$$

### The Golden `"banana"` Example

| Rank $k$ | Suffix Start $sa[k]$ | Suffix String |
| :---: | :---: | :--- |
| **0** | **5** | `"a"` |
| **1** | **3** | `"ana"` |
| **2** | **1** | `"anana"` |
| **3** | **0** | `"banana"` |
| **4** | **4** | `"na"` |
| **5** | **2** | `"nana"` |

Thus, for `"banana"`, the golden Suffix Array permutation is:

$$sa = [5, 3, 1, 0, 4, 2]$$

---

## 2. Fast Substring Search via Binary Search ($O(m \log n)$)

Because all suffixes are sorted lexicographically, every occurrence of any query pattern $P$ of length $m$ must appear as a prefix of a contiguous range of suffixes in $sa$.

### Search Algorithm:
1. Initialize binary search bounds: $\text{low} = 0, \text{high} = n - 1$.
2. Compute midpoint: $\text{mid} = \lfloor (\text{low} + \text{high}) / 2 \rfloor$.
3. Compare pattern $P$ against the first $m$ characters of the suffix starting at $sa[\text{mid}]$:
   - If equal, pattern is found; return starting index $sa[\text{mid}]$.
   - If $P$ is lexicographically greater, advance $\text{low} = \text{mid} + 1$.
   - If $P$ is lexicographically smaller, retreat $\text{high} = \text{mid} - 1$.
4. Total comparisons: $\lceil \log_2 n \rceil$, each taking at most $m$ character checks, yielding total latency **$O(m \log n)$**.

---

## 3. Lateralus Reference Implementation

```lateralus
fn compare_suffixes(text, n, i, j) {
    let p = i
    let q = j
    while p < n and q < n {
        let ch1 = text[p]
        let ch2 = text[q]
        if ch1 < ch2 {
            return -1
        }
        if ch1 > ch2 {
            return 1
        }
        p = p + 1
        q = q + 1
    }
    if p == n and q == n {
        return 0
    }
    if p == n {
        return -1
    }
    return 1
}

pub fn build_suffix_array(text) {
    let n = len(text)
    let sa = []
    let i = 0
    while i < n {
        sa = push(sa, i)
        i = i + 1
    }

    let a = 1
    while a < n {
        let key = sa[a]
        let b = a - 1
        while b >= 0 {
            let prev = sa[b]
            if compare_suffixes(text, n, prev, key) > 0 {
                sa[b + 1] = prev
                b = b - 1
            } else {
                break
            }
        }
        sa[b + 1] = key
        a = a + 1
    }

    return sa
}

pub fn sa_search(text, sa, pattern) {
    let n = len(text)
    let m = len(pattern)
    if m == 0 or n == 0 {
        return -1
    }

    let low = 0
    let high = n - 1

    while low <= high {
        let mid = (low + high) / 2
        let suffix_start = sa[mid]
        let cmp = compare_prefix(text, n, suffix_start, pattern, m)

        if cmp == 0 {
            return suffix_start
        }
        if cmp < 0 {
            low = mid + 1
        } else {
            high = mid - 1
        }
    }

    return -1
}
```

---

## 4. Architectural Comparison: Suffix Array vs. Suffix Tree

| Dimension | Suffix Array (SA) | Suffix Tree |
| :--- | :---: | :---: |
| **Auxiliary Memory** | **$4n$ bytes (Flat Integer Array)** | $16n \dots 32n$ bytes (Pointers + Tuples) |
| **Search Query Time** | $O(m \log n)$ | $O(m)$ |
| **Cache Locality** | High (Contiguous memory access) | Low (Node pointer chasing) |
| **Implementation Complexity** | Simple & Compact (~60 lines) | High (Ukkonen's implicit transitions) |

---

## 5. Industrial Applications

1. **Bioinformatics & Genomics (BLAST / Bowtie / BWA)**:
   Indexing billion-base-pair human genome assemblies for ultra-fast short-read sequence alignment.
2. **Burrows-Wheeler Transform (BWT)**:
   Serving as the precomputation permutation underlying bzip2 and modern compression utilities.
3. **Plagiarism Detection & Document Deduplication**:
   Locating longest common substrings across vast multi-document repositories in constant auxiliary memory.
