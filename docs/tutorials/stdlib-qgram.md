# Typo-Tolerant Search & Fuzzy Indexing with `stdlib.qgram`

The Lateralus standard library provides `stdlib/qgram.ltl`, implementing $q$-gram (character $n$-gram) tokenization and inverted index construction for approximate string matching. This technique serves as an ultra-fast $O(1)$ pre-filter for fuzzy search engines before executing exact edit-distance dynamic programming.

---

## API Summary

| Function | Signature | Description |
|---|---|---|
| `qgrams(text, q)` | `(str, int) -> list` | Generates overlapping character windows padded with prefix/suffix anchors |
| `overlap(a, b, q)` | `(str, str, int) -> int` | Counts identical shared $q$-grams between two strings |
| `jaccard(a, b, q)` | `(str, str, int) -> float` | Computes Jaccard similarity index: $\frac{|A \cap B|}{|A \cup B|} \in [0.0, 1.0]$ |
| `build_index(docs, q)` | `(list, int) -> dict` | Constructs an inverted index mapping each $q$-gram to a list of doc IDs |
| `query(index, text, q)` | `(dict, str, int) -> list` | Evaluates a search query and returns ranked `[doc_id, score]` pairs |

---

## Runnable Example

```lateralus
import qgram

fn main() {
    let docs = [
        "lateralus programming language",
        "python asynchronous architecture",
        "ladder logic industrial automation"
    ]

    // Construct 2-gram inverted index
    let idx = build_index(docs, 2)

    // Search with misspelled keyword "lateralluss"
    let matches = query(idx, "lateralluss", 2)
    println("Top match doc id: " + str(matches[0][0]))

    // Measure typo similarity
    let sim = jaccard("algorithm", "algoritm", 2)
    println("Similarity: " + str(sim))
}

main()
```

### Output
```text
Top match doc id: 0
Similarity: 0.7272727272727273
```
