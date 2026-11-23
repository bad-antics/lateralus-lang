# Standard Library Deep Dive: Aho-Corasick Multi-Pattern String Matching Automaton

The **Aho-Corasick algorithm**, published by Alfred V. Aho and Margaret J. Corasick in 1975, is a seminal multi-pattern string searching algorithm. Given an input text of length $N$ and a dictionary of $k$ distinct pattern strings with aggregate length $M = \sum |P_i|$, the algorithm locates all occurrences of all dictionary patterns simultaneously in **$O(N + M + Z)$** time, where $Z$ is the total count of pattern matches.

In contrast to iterating single-pattern algorithms like KMP $k$ times ($O(k \cdot N + M)$), Aho-Corasick achieves linear scalability with respect to the input stream length $N$, completely independent of the dictionary size $k$.

---

## 1. Architectural Foundation: Trie + KMP Failure Links

Aho-Corasick synthesizes two core ideas:
1. **The Trie (Prefix Tree)**: Compactly represents the dictionary and groups shared prefixes into common branches.
2. **Failure Links (Suffix Fallbacks)**: Inspired by Knuth-Morris-Pratt (KMP), when a character mismatch occurs during text ingestion, the automaton does not restart from the root. Instead, it follows a directed **failure pointer** to the longest proper suffix that exists elsewhere in the Trie.

```
                     Root (0)
                   /          \
                's'            'h'
                /                \
             Node 1            Node 3 ("he")
             /                   /    \
          'h'                  'r'    'i'
          /                    /        \
       Node 2 ("she")       Node 4     Node 5 ("his")
                            /
                         Node 6 ("hers")

Failure Link: Node 2 ("she") -> Node 3 ("he")
```

---

## 2. Three-Phase Execution Lifecycle

### Phase 1: Trie Construction ($O(M)$)
All patterns $P_1, \dots, P_k$ are inserted into a standard prefix tree. Each terminal node registers its pattern string in its `output` list.

### Phase 2: BFS Failure Link Resolution ($O(M)$)
Using Breadth-First Search (BFS):
1. **Depth 1 Nodes**: All immediate children of the root have their failure link assigned to the root node (0). These are enqueued.
2. **Deeper Nodes ($v$ with character $c$ from parent $u$)**:
   - Trace backwards starting from $u$'s failure link: $f = \text{fail}[u]$.
   - While $f \ne 0$ and $f$ has no child transition for character $c$, traverse $f \leftarrow \text{fail}[f]$.
   - If a matching transition exists, set $\text{fail}[v] \leftarrow \text{child}(f, c)$; otherwise set $\text{fail}[v] \leftarrow 0$.
3. **Output Link Inheritance**:
   - If $\text{fail}[v]$ has non-empty output patterns (such as a shorter pattern nested inside a longer one, e.g., "he" inside "she"), merge $\text{output}[\text{fail}[v]]$ directly into $\text{output}[v]$.

### Phase 3: Single-Pass Text Ingestion ($O(N)$)
For each character in the input stream $T$:
- Follow transitions down the automaton.
- If no matching outbound edge exists, fall back along failure links until a transition is valid or root is reached.
- Append all patterns listed in the current state's `output` array to the result match set.

---

## 3. Lateralus Reference Implementation

```lateralus
pub fn ac_build_failure_links(ac) {
    let nodes = ac["nodes"]
    let queue = []
    let root = nodes[0]

    let next_ids = root["next_ids"]
    let i = 0
    while i < len(next_ids) {
        let child_id = next_ids[i]
        nodes[child_id]["fail"] = 0
        queue = push(queue, child_id)
        i = i + 1
    }

    let q_head = 0
    while q_head < len(queue) {
        let u_id = queue[q_head]
        q_head = q_head + 1
        let u_node = nodes[u_id]

        let u_keys = u_node["keys"]
        let u_nexts = u_node["next_ids"]
        let k = 0
        while k < len(u_keys) {
            let ch = u_keys[k]
            let v_id = u_nexts[k]
            let v_node = nodes[v_id]

            let f_id = u_node["fail"]
            let matched_fail = -1
            while f_id != 0 and matched_fail == -1 {
                let candidate = get_child(nodes[f_id], ch)
                if candidate != -1 {
                    matched_fail = candidate
                } else {
                    f_id = nodes[f_id]["fail"]
                }
            }

            if matched_fail == -1 {
                let root_child = get_child(nodes[0], ch)
                if root_child != -1 and root_child != v_id {
                    matched_fail = root_child
                } else {
                    matched_fail = 0
                }
            }

            v_node["fail"] = matched_fail

            let fail_outputs = nodes[matched_fail]["output"]
            let p = 0
            while p < len(fail_outputs) {
                v_node["output"] = push(v_node["output"], fail_outputs[p])
                p = p + 1
            }

            queue = push(queue, v_id)
            k = k + 1
        }
    }
}
```

---

## 4. Complexity & Theoretical Bounds

| Operation | Time Complexity | Auxiliary Space |
| :--- | :---: | :---: |
| **Dictionary Ingestion** | $O(M)$ | $O(M)$ states |
| **BFS Failure Links** | $O(M)$ | $O(M)$ queue |
| **Online Text Scanning** | **$O(N + Z)$** | $O(Z)$ output matches |
| **Total Pipeline** | **$O(N + M + Z)$** | **Strictly Linear $O(M)$** |

*(where $N = |T|$, $M = \sum |P_i|$, and $Z$ is total number of occurrences).*

---

## 5. Industrial Applications

1. **Intrusion Detection Systems (IDS - Snort / Suricata)**:
   Simultaneously scanning gigabits of packet payload against tens of thousands of threat signatures in real-time.
2. **Web Application Firewalls (WAF)**:
   Instant multi-keyword sanitization blocking SQL injection (`UNION`, `SELECT`), cross-site scripting (`<script>`), and directory traversal attack vectors.
3. **Bioinformatics DNA Motif Hunting**:
   Concurrently identifying multiple CRISPR guide RNA sequences or restriction enzyme recognition sites across millions of base-pair sequences.
4. **GNU `grep -F` (fgrep)**:
   Powers fast fixed-string searching when matching against large lists of search patterns.
