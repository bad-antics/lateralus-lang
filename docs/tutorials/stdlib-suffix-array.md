# Substring Search & Repeated Sequences with `stdlib.suffix_array`

A **Suffix Array** is an array of integers representing the starting positions of all suffixes of a string, sorted in lexicographical order. When combined with Kasai's **Longest Common Prefix (LCP)** array, it provides an efficient index for fast substring pattern queries, genomic sequence alignment, and repeated substring identification.

The Lateralus standard library provides `stdlib/suffix_array.ltl`.

---

## API Summary

| Function | Complexity | Description |
|---|---|---|
| `build(text)` | $O(n \log^2 n)$ | Builds the sorted suffix array index via prefix-doubling |
| `lcp(text, sa)` | $O(n)$ | Computes Kasai's LCP array measuring prefix overlap between adjacent sorted suffixes |
| `search(text, sa, pattern)` | $O(m \log n)$ | Binary-searches the suffix array for pattern occurrences |
| `longest_repeated(text)` | $O(n)$ | Finds the longest repeating substring by locating the maximum LCP entry |

---

## Canonical Example: `"banana"`

The suffixes of `"banana"` sorted alphabetically:

| Rank | Start Index (`SA`) | Suffix String | LCP with Preceding Suffix |
|---|---|---|---|
| 0 | `5` | `"a"` | `0` |
| 1 | `3` | `"ana"` | `1` (`"a"`) |
| 2 | `1` | `"anana"` | `3` (`"ana"`) |
| 3 | `0` | `"banana"` | `0` |
| 4 | `4` | `"na"` | `0` |
| 5 | `2` | `"nana"` | `2` (`"na"`) |

- **Suffix Array:** `[5, 3, 1, 0, 4, 2]`
- **LCP Array:** `[0, 1, 3, 0, 0, 2]`
- **Longest Repeated Substring:** `"ana"` (length 3, from LCP index 2)

---

## Runnable Example

```lateralus
import suffix_array

fn main() {
    let word = "banana"
    let sa = build(word)
    println("SA: " + str(sa))

    let l = lcp(word, sa)
    println("LCP: " + str(l))

    let rep = longest_repeated(word)
    println("Longest repeated: " + rep)

    let idx = search(word, sa, "ana")
    println("Index of 'ana': " + str(idx))
}

main()
```
