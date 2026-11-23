# Mastering Prefix Tries in Lateralus: O(K) Lookup Trees, Route Dispatch, and Autocompletion

Hash tables offer excellent $O(1)$ average-case lookup for exact keys, but they fail completely when applications require:
- Prefix matching (`starts_with("app")`)
- Autocompletion suggestions (listing all entries beginning with `geo_`)
- Longest Common Prefix (LCP) evaluation
- Hierarchical routing (grouping endpoints under `/api/v1/*`)

A **Trie (Prefix Tree)** organizes associative keys along string edges, guaranteeing retrieval, insertion, and prefix frequency queries in $O(K)$ time (where $K$ is the length of the search key), completely independent of total dataset size $N$.

In this tutorial, we demonstrate how to construct, traverse, and benchmark Prefix Tries in Lateralus.

---

## 1. Architectural Model: Shared Common Paths

A Trie represents characters as transitions between nodes:

```
         (root)
        /      \
      "a"      "b"
       |        |
      "p"      "a"
       |        |
      "p"*     "n"
     /   \      |
   "l"   "t"*  "a"
    |           |
   "e"*        "n"
                |
               "a"*
```
Asterisks (`*`) denote terminal nodes (words: `"app"`, `"apple"`, `"apt"`, `"banana"`).

Keys sharing prefixes reuse intermediate nodes, drastically reducing memory footprint compared to duplicate string copies.

---

## 2. Dynamic Traversal & Frequency Counting

For every inserted key, prefix transitions record occurrence frequency:

```lateralus
fn trie_insert(exact_map: dict, prefix_map: dict, word: string) -> int {
    exact_map[word] = 1;
    let w_len = len(word);
    let mut i = 1;
    while i <= w_len {
        let pref = slice(word, 0, i);
        let mut curr_count = 0;
        if contains(prefix_map, pref) {
            curr_count = prefix_map[pref];
        }
        prefix_map[pref] = curr_count + 1;
        i = i + 1;
    }
    return 0;
}
```

---

## 3. Real-World API Gateway Prefix Routing

In HTTP edge proxies and API gateways, incoming requests map dynamically to backend service pools based on URI prefixes (e.g., routing all `/api/v1/*` to legacy clusters and `/api/v2/*` to modern container pools).

See `examples/trie_tutorial.ltl` for a runnable demonstration routing multiple endpoints without linear table scans.

---

## 4. End-to-End Verification with Golden Vectors

We assert compliance across typical key distributions:
- Exact string membership and non-terminal prefix rejection.
- Empty prefix boundary assertions (`""` matches non-empty tries).
- Prefix frequency cardinality verification (`"app"` prefix count = 3).

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/trie_tutorial.ltl
python -m lateralus_lang check tests/stdlib_trie_tutorial.ltl
pytest tests/test_compiler.py
```
