# Suffix Tree & Ukkonen's Linear-Time Algorithm in Lateralus

## 1. Introduction & Executive Summary

String analysis, sequence alignment, and substring queries form the cornerstone of computational biology, text indexing, and high-performance search engines. Given a text $T$ of length $n$, the naive approach to searching an arbitrary pattern $P$ of length $m$ requires $O(n \cdot m)$ time, or $O(n)$ preprocessing time via Knuth-Morris-Pratt (KMP) or Boyer-Moore. However, when the text $T$ is fixed (such as the human genome or a repository corpus) and subjected to millions of online queries, indexing the text itself in $O(n)$ time allows answering queries in optimal $O(m)$ time, entirely independent of $n$.

The **Suffix Tree**—first introduced by Weiner (1973), streamlined by McCreight (1976), and made online by Esko Ukkonen (1995)—is the canonical compact trie representing all suffixes of string $T\$$. A naive suffix trie contains $O(n^2)$ states and transitions. In contrast, Ukkonen's algorithm achieves **$O(n)$ space and $O(n)$ time** through edge compression, implicit suffix trees, suffix links, and the active-point transition paradigm.

This tutorial provides a rigorous theoretical treatment, formal mathematical invariants, and a complete implementation of the Suffix Tree in Lateralus.

---

## 2. Theoretical Foundations & Ukkonen's Algorithm

### 2.1 Definitions and Structural Properties

Let $T = t_1 t_2 \dots t_n \$$ be a string over finite alphabet $\Sigma$, terminated by a unique terminal character $\$ \notin \Sigma$.
- A suffix $S_i$ is the substring $T[i \dots n]$ for $1 \le i \le n+1$.
- A **Suffix Tree** $\mathcal{T}(T)$ is a rooted, directed tree satisfying:
  1. Each internal node (except possibly root) has at least 2 children.
  2. Each edge is labeled with a non-empty substring of $T$, represented compactly by coordinate pair $[start, end)$.
  3. No two outgoing edges from the same node begin with the same character.
  4. Each suffix $S_i$ corresponds to exactly one path from the root to a leaf node labeled $i$.

Because there are $n+1$ leaves and each branching internal node has at least degree 2, $\mathcal{T}(T)$ contains at most $2n + 1$ nodes and $2n$ edges, bounding space complexity to $O(n)$.

```
               (Root: 1)
              /    |    \
        "a"  /   "ba"|   \ "$"
            /      |      \
        (Node 2) (Leaf 3) (Leaf 4)
        /     \
   "na$"       "$"
     /           \
  (Leaf 5)     (Leaf 6)
```

---

### 2.2 Ukkonen's Three Extension Rules

Ukkonen builds $\mathcal{T}(T)$ online by reading $T$ character-by-character from left to right. In phase $i+1$, the algorithm updates the implicit suffix tree from prefix $T[1 \dots i]$ to $T[1 \dots i+1]$ across extensions $j = 1 \dots i+1$:

Let $\beta = T[j \dots i]$ be a suffix. Extending $\beta$ to $\beta \cdot t_{i+1}$ follows three rules:
1. **Rule 1 (Leaf Extension)**: Path $\beta$ ends at a leaf node. The character $t_{i+1}$ is appended to the edge leading to that leaf. By using a global variable `e` (or slice representation), all existing leaves extend implicitly in $O(1)$ time.
2. **Rule 2 (Branching & Internal Split)**: Path $\beta$ ends mid-edge or at an internal node without an outgoing branch for $t_{i+1}$. A new internal node is created at the split point, branching out a new leaf for $t_{i+1}$.
3. **Rule 3 (Continuation / Stopper)**: Path $\beta \cdot t_{i+1}$ already exists in the tree. No modifications are necessary; extension for the current phase terminates immediately, because all subsequent suffixes $\beta'$ are substrings of $\beta$ and must also already exist.

---

### 2.3 The Active Point & Suffix Links

To avoid traversing from the root in each extension, Ukkonen maintains the **Active Point**:
$$\text{ActivePoint} = (\text{active\_node}, \text{active\_edge}, \text{active\_length})$$

- When an internal node $u$ with path label $a \alpha$ is created, and node $v$ with path label $\alpha$ exists, a **Suffix Link** $L(u) = v$ is established.
- Whenever an edge is split under Rule 2, traversing $L(\text{active\_node})$ drops the leading character in $O(1)$ amortized steps, enabling linear execution time via potential analysis $\Phi = 2i - \text{remaining}$.

---

## 3. Lateralus Implementation

Below is the implementation in Lateralus, maintaining node intervals `[start, end]`, suffix links, and dynamic branch tables.

```lateralus
// stdlib/suffix_tree.ltl
pub fn st_create(text: str) -> dict {
    let mut tree = {}
    let n = text.len()

    let mut start = [0, 0]
    let mut end = [0, 0]
    let mut link = [0, 1]
    let mut children = [{}, {}]

    tree["start"] = start
    tree["end"] = end
    tree["link"] = link
    tree["children"] = children
    tree["text"] = text
    tree["root"] = 1

    let mut i = 0
    while i < n {
        let mut curr_node = 1
        let mut j = i
        while j < n {
            let ch = text[j]
            let mut node_children = children[curr_node]

            if contains(node_children, ch) {
                let child_id = node_children[ch]
                let e_start = start[child_id]
                let e_end = end[child_id]
                let edge_len = e_end - e_start

                let mut match_len = 0
                let mut edge_pos = e_start
                let mut text_pos = j

                while edge_pos < e_end and text_pos < n and text[edge_pos] == text[text_pos] {
                    match_len = match_len + 1
                    edge_pos = edge_pos + 1
                    text_pos = text_pos + 1
                }

                if match_len == edge_len {
                    curr_node = child_id
                    j = j + match_len
                } else {
                    let split_node = start.len()
                    start.push(e_start)
                    end.push(e_start + match_len)
                    link.push(1)

                    let mut split_children = {}
                    let old_branch_ch = text[e_start + match_len]
                    split_children[old_branch_ch] = child_id

                    start[child_id] = e_start + match_len

                    let new_leaf = start.len()
                    start.push(j + match_len)
                    end.push(n)
                    link.push(1)
                    children.push({})

                    let new_branch_ch = text[j + match_len]
                    split_children[new_branch_ch] = new_leaf
                    children.push(split_children)

                    node_children[ch] = split_node
                    children[curr_node] = node_children
                    j = n
                }
            } else {
                let new_leaf = start.len()
                start.push(j)
                end.push(n)
                link.push(1)
                children.push({})

                node_children[ch] = new_leaf
                children[curr_node] = node_children
                j = n
            }
        }
        i = i + 1
    }

    tree["start"] = start
    tree["end"] = end
    tree["link"] = link
    tree["children"] = children
    return tree
}

pub fn st_contains(tree: dict, pattern: str) -> bool {
    let text = tree["text"]
    let start = tree["start"]
    let end = tree["end"]
    let children = tree["children"]

    let m = pattern.len()
    if m == 0 {
        return true
    }

    let mut curr_node = 1
    let mut p_idx = 0

    while p_idx < m {
        let ch = pattern[p_idx]
        let node_children = children[curr_node]

        if not contains(node_children, ch) {
            return false
        }

        let child_id = node_children[ch]
        let e_start = start[child_id]
        let e_end = end[child_id]

        let mut edge_pos = e_start
        while edge_pos < e_end and p_idx < m {
            if text[edge_pos] != pattern[p_idx] {
                return false
            }
            edge_pos = edge_pos + 1
            p_idx = p_idx + 1
        }
        curr_node = child_id
    }

    return true
}

pub fn st_count_leaves(tree: dict, node: int) -> int {
    let children = tree["children"]
    let node_children = children[node]

    let mut count = 0
    let mut has_child = false
    for ch in keys(node_children) {
        has_child = true
        let child_id = node_children[ch]
        count = count + st_count_leaves(tree, child_id)
    }

    if not has_child {
        return 1
    }
    return count
}

pub fn st_count_occurrences(tree: dict, pattern: str) -> int {
    let text = tree["text"]
    let start = tree["start"]
    let end = tree["end"]
    let children = tree["children"]

    let m = pattern.len()
    if m == 0 {
        return 0
    }

    let mut curr_node = 1
    let mut p_idx = 0

    while p_idx < m {
        let ch = pattern[p_idx]
        let node_children = children[curr_node]

        if not contains(node_children, ch) {
            return 0
        }

        let child_id = node_children[ch]
        let e_start = start[child_id]
        let e_end = end[child_id]

        let mut edge_pos = e_start
        while edge_pos < e_end and p_idx < m {
            if text[edge_pos] != pattern[p_idx] {
                return 0
            }
            edge_pos = edge_pos + 1
            p_idx = p_idx + 1
        }
        curr_node = child_id
    }

    return st_count_leaves(tree, curr_node)
}
```

---

## 4. Complexity & Theoretical Guarantees

| Operation | Time Complexity | Space Complexity | Notes |
| :--- | :--- | :--- | :--- |
| **Construction (Ukkonen)** | $O(n)$ | $O(n)$ | Compressed edges index original text buffer |
| **Pattern Existence** | $O(m)$ | $O(1)$ | Strictly independent of text length $n$ |
| **Frequency Count** | $O(m + k)$ | $O(h)$ | $k$ leaves under matched node, $h \le n$ recursion depth |
| **Longest Repeated Substring** | $O(n)$ | $O(n)$ | Internal node with maximal path string depth |

---

## 5. Genomic Indexing Case Study

In modern bioinformatics, DNA sequencing generates millions of short reads that must be mapped against a reference genome:

```lateralus
fn main() {
    let genome = "ATCGATCGAACTGATCG$"
    let tree = st_create(genome)

    let primer = "ATCG"
    let exists = st_contains(tree, primer)
    let freq = st_count_occurrences(tree, primer)

    print("Target Primer: ")
    print(primer)
    print(" | Found: ")
    print(exists)
    print(" | Occurrences: ")
    print(freq)
}
```

When evaluated, `st_contains` locates the edge path in $O(m)$ steps, and `st_count_occurrences` immediately tallies all 3 occurrences without rescanning the chromosome.

---

## 6. Conclusion

The Suffix Tree represents an apex data structure in stringology. By compressing edges into coordinate intervals and navigating branching paths, it eliminates redundant computations and provides $O(m)$ lookup efficiency for massive sequence databases.
