# Standard Library Deep Dive: Trie (Prefix Tree) & Autocomplete Engine

The **Trie** (derived from re*trie*val, introduced by René de la Briandais in 1959 and named by Edward Fredkin in 1960) is an optimal ordered tree data structure designed for dynamic string dictionary indexing, prefix filtering, and predictive autocompletion.

While standard hash tables achieve expected $O(L)$ average lookups for exact keys (where $L$ is key length), they are fundamentally incapable of efficient prefix range queries or predictive suggestions without scanning the entire key space ($O(N \cdot L)$). Conversely, balanced search trees require $O(L \log N)$ comparisons. The Trie decouples search complexity entirely from the total number of stored entries $N$, guaranteeing deterministic **$O(L)$** insertion, search, and prefix detection.

---

## 1. Algorithmic Architecture & Node Layout

In a standard Trie, common prefixes are shared across branches. Each node represents a prefix state, with outbound edges representing character transitions.

```
                     Root (0)
                   /          \
                'c'            'm'
                /                \
             Node 1            Node 4
             /    \            /    \
           'o'    'a'        'a'    'e'
           /        \        /        \
        Node 2    Node 3   Node 5   Node 6
       ("co")    ("ca")   ("ma")   ("me")
```

### Decoupled Key-Index Representation

To remain fully cross-target compatible across WASM, C, and Python runtimes without relying on fixed 26-letter ASCII assumptions or language-specific hash maps, each Trie node is structured with parallel dynamic arrays:

- `keys`: Dynamic list of outbound characters `['a', 'b', ...]`.
- `next_ids`: Corresponding target node indices `[12, 18, ...]`.
- `is_end`: Boolean flag marking valid terminal words.
- `freq`: Numerical popularity weight for ranking suggestions.
- `word`: Cached full terminal string, accelerating leaf collection without upward parent traversal.

---

## 2. Core Operation Walkthrough

### 2.1 Insertion ($O(L)$)
Iterate character-by-character through input string $w$ of length $L$:
1. At node $u$, query `get_child_id(u, w[i])`.
2. If found, transition to the child node.
3. If absent, allocate a new node at index `len(nodes)`, register the transition in $u$, and advance.
4. Mark the terminal node with `is_end = true` and record its popularity score.

### 2.2 Prefix Search & Autocompletion
Given query prefix $P$:
1. Traverse downward from the root following characters of $P$.
2. If any character transition is missing, $P$ does not exist in the dictionary; return empty immediately.
3. Upon reaching the node corresponding to the full prefix $P$, perform a Depth-First Search (DFS) over its entire subtree to collect all descendant terminal words.

```lateralus
fn collect_words_dfs(nodes, curr_id, results) {
    let curr_node = nodes[curr_id]
    if curr_node["is_end"] {
        results = push(results, curr_node["word"])
    }

    let next_ids = curr_node["next_ids"]
    let i = 0
    let n = len(next_ids)
    while i < n {
        let nxt = next_ids[i]
        results = collect_words_dfs(nodes, nxt, results)
        i = i + 1
    }
    return results
}
```

---

## 3. Lateralus Reference Implementation

```lateralus
pub fn trie_insert(trie, word, freq) {
    let nodes = trie["nodes"]
    let curr_id = 0
    let n = len(word)
    let i = 0

    while i < n {
        let ch = word[i]
        let curr_node = nodes[curr_id]
        let next_id = get_child_id(curr_node, ch)

        if next_id != -1 {
            curr_id = next_id
        } else {
            let new_id = len(nodes)
            let new_node = make_trie_node(new_id)
            nodes = push(nodes, new_node)
            trie["nodes"] = nodes
            put_child(curr_node, ch, new_id)
            curr_id = new_id
        }
        i = i + 1
    }

    let end_node = nodes[curr_id]
    end_node["is_end"] = true
    end_node["freq"] = freq
    end_node["word"] = word
}

pub fn trie_autocomplete(trie, prefix) {
    let nodes = trie["nodes"]
    let curr_id = 0
    let n = len(prefix)
    let i = 0

    while i < n {
        let ch = prefix[i]
        let curr_node = nodes[curr_id]
        let next_id = get_child_id(curr_node, ch)

        if next_id == -1 {
            return []
        }
        curr_id = next_id
        i = i + 1
    }

    let results = []
    return collect_words_dfs(nodes, curr_id, results)
}
```

---

## 4. Complexity Analysis

| Operation | Time Complexity | Space Complexity |
| :--- | :---: | :---: |
| **Insert** | $O(L)$ | $O(L)$ (worst case new nodes) |
| **Exact Search** | $O(L)$ | $O(1)$ auxiliary |
| **Prefix Check (`starts_with`)** | $O(L)$ | $O(1)$ auxiliary |
| **Autocomplete (`suggest`)** | $O(L + K \cdot M)$ | $O(K \cdot M)$ (result set) |

*(where $L$ is query prefix length, $K$ is number of matching words, and $M$ is average matching word length).*

---

## 5. Industrial Applications

1. **Language Server Protocol (LSP) & IDE Code Completion**:
   Instantly suggest language keywords, scope identifiers, and API methods as the developer types.
2. **Search Engine Query Suggestions**:
   Predictive query autocompletion with weighted popularity ranking on search bars.
3. **Network Routing & Longest Prefix Matching**:
   IP address longest-prefix matching in routers and firewall packet inspection.
4. **Multi-Pattern String Matching (Aho-Corasick)**:
   The Trie serves as the core automaton skeleton for the Aho-Corasick multi-pattern search algorithm used in intrusion detection systems (Snort, Suricata).
