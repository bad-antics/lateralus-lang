# Fast Prefix Autocompletion with `stdlib.trie`

The Lateralus standard library ships `stdlib/trie.ltl`, a tree data structure optimized for fast string retrieval, prefix querying, and lexical routing. This tutorial demonstrates how to build an autocomplete and command router for command-line interfaces or URL routing tables.

---

## Core API Reference

| Function | Signature | Description |
|---|---|---|
| `new()` | `() -> map` | Creates an empty root trie node |
| `from_words(words)` | `(list) -> map` | Builds a trie pre-populated with a list of words |
| `insert(t, key, value)` | `(map, str, any) -> map` | Inserts or updates a key and its associated value |
| `has(t, key)` | `(map, str) -> bool` | Returns `true` if the exact key exists in the trie |
| `has_prefix(t, prefix)` | `(map, str) -> bool` | Returns `true` if any key starts with `prefix` |
| `keys_with_prefix(t, prefix)` | `(map, str) -> list` | Returns all keys starting with `prefix` |
| `count_prefix(t, prefix)` | `(map, str) -> int` | Counts total keys sharing the given prefix |
| `longest_prefix(t, word)` | `(map, str) -> str` | Finds the longest key in the trie that is a prefix of `word` |

---

## Runnable Example

```lateralus
import trie

fn main() {
    let commands = ["help", "history", "status", "start", "stop", "restart", "stats"]
    let router = from_words(commands)

    // Prefix lookups for user input autocompletion
    let suggestions = keys_with_prefix(router, "st")
    println("Suggestions for 'st': " + str(suggestions))

    // Longest prefix route matching
    let route = longest_prefix(router, "startup")
    println("Matched route: " + route)
}

main()
```

### Output
```text
Suggestions for 'st': ["start", "stats", "status", "stop"]
Matched route: start
```
