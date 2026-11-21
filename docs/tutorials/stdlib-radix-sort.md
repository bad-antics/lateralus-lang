# High-Performance $O(n)$ Sorting with `stdlib.radix_sort`

Comparison-based sorts (such as QuickSort or MergeSort) are bounded by $\Omega(n \log n)$ time complexity. When keys are integers, fixed-width words, or strings, non-comparison sorts execute in linear $O(n)$ time by partitioning items into radix buckets. The Lateralus standard library provides `stdlib/radix_sort.ltl` for high-throughput batch sorting.

---

## Functions Reference

| Function | Complexity | Description |
|---|---|---|
| `radix_sort_u32(xs)` | $4n = O(n)$ | 4-pass Least-Significant-Digit (LSD) byte radix sort for unsigned 32-bit integers |
| `radix_sort_u64(xs)` | $8n = O(n)$ | 8-pass LSD byte radix sort for unsigned 64-bit integers |
| `radix_sort_i32(xs)` | $4n = O(n)$ | Signed 32-bit sort via sign-bit inversion (`x ^ 0x80000000`) before/after LSD passes |
| `radix_sort_str(xs)` | $O(n \cdot L)$ | Most-Significant-Digit (MSD) recursive character bucket sort for strings |
| `counting_sort(xs, k)` | $O(n + k)$ | Stable counting sort for small non-negative integers bounded by $k$ |

---

## Runnable Example

```lateralus
import radix_sort

fn main() {
    // Unsigned integer sorting
    let u = [170, 45, 75, 90, 802, 24, 2, 66]
    println("U32: " + str(radix_sort_u32(u)))

    // Signed integer sorting
    let i = [170, -45, 75, -90, 802, -24, 2, -66, 0]
    println("I32: " + str(radix_sort_i32(i)))

    // String lexicographical sorting
    let words = ["banana", "apple", "cherry", "date", "apricot"]
    println("Strings: " + str(radix_sort_str(words)))
}

main()
```

### Output
```text
U32: [2, 24, 45, 66, 75, 90, 170, 802]
I32: [-90, -66, -45, -24, 0, 2, 75, 170, 802]
Strings: ["apple", "apricot", "banana", "cherry", "date"]
```
