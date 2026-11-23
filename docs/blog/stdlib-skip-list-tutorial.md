# Skip List Probabilistic Multi-Level Data Structure in Lateralus

## 1. Introduction

Maintaining dynamic ordered collections with fast retrieval, insertion, and range queries is a fundamental requirement in systems engineering. While classical **Balanced Binary Search Trees** (such as AVL trees or Red-Black trees) guarantee worst-case $\mathcal{O}(\log n)$ performance, their maintenance requires intricate structural tree rotations. Under concurrent or distributed workloads, rebalancing rotations create widespread lock contention and cache invalidations.

Invented by William Pugh in 1990, the **Skip List** replaces rigid structural invariants with **probabilistic geometric promotions**:

$$\text{Expected Operations: } \mathcal{O}(\log n) \text{ Search, Insert, and Delete}$$

A Skip List consists of a hierarchy of linked lists. At the baseline (Level 0), all elements are linked in ascending sorted order. Each higher level acts as an **express lane**, skipping over geometric fractions of elements.

Because node elevations are determined by independent pseudo-random coin tosses rather than global balance constraints, skip lists are straightforward to implement and represent the standard architecture for:
- **Redis Sorted Sets (`ZSET`)**: Fueling global real-time leaderboards.
- **LevelDB / RocksDB `MemTable`**: High-throughput concurrent in-memory write buffers for Log-Structured Merge (LSM) storage engines.
- **Apache Lucene**: Accelerating search index term postings list lookups.

This tutorial provides a complete walkthrough of implementing Skip Lists in Lateralus (`stdlib/skip_list.ltl`), complete with high-throughput gaming leaderboard indexing and golden test vectors.

---

## 2. Mathematical Principles & Multi-Level Traversal

### 2.1 Geometric Distribution of Tower Heights
When a new key is inserted, its tower height $k$ is drawn from a geometric distribution with promotion probability $p = 1/2$:
- Level 0 contains $100\%$ of elements.
- Level 1 contains approximately $50\%$ of elements.
- Level 2 contains approximately $25\%$ of elements.
- Level $h$ contains approximately $n \cdot p^h$ elements.

With maximum level $L = \lceil \log_{1/p} n \rceil$, the total expected number of forward pointers across all nodes is:

$$\sum_{k=0}^{\infty} n p^k = \frac{n}{1 - p} = 2n \quad (\text{for } p = 1/2)$$

This incurs only a minimal, linear memory footprint.

### 2.2 Express Lane Search Mechanism
To search for a target key:
1. Start at the top active level of the head sentinel node.
2. Greedily advance forward as long as the next node's key is strictly less than the target key.
3. When the next node exceeds the target or reaches the end of the level, drop down one level.
4. Repeat until reaching Level 0. If the next node at Level 0 matches the target key, the element is found!

The expected number of horizontal and vertical steps is bounded by $\mathcal{O}(\log n)$.

---

## 3. Lateralus Implementation

Here is the complete implementation in Lateralus:

```lateralus
pub fn create_skip_list(max_level) {
    let sl = dict()
    sl["max_level"] = max_level
    sl["current_level"] = 1
    sl["seed"] = 42

    let head = dict()
    head["key"] = -999999999
    head["val"] = nil
    head["forward"] = dict()

    let lvl = 0
    while lvl < max_level {
        head["forward"][lvl] = -1
        lvl = lvl + 1
    }

    sl["nodes"] = [head]
    return sl
}

pub fn skip_list_search(sl, target_key) {
    let curr_idx = 0
    let lvl = sl["current_level"] - 1

    while lvl >= 0 {
        let done = false
        while not done {
            let next_idx = sl["nodes"][curr_idx]["forward"][lvl]
            if next_idx != -1 and sl["nodes"][next_idx]["key"] < target_key {
                curr_idx = next_idx
            } else {
                done = true
            }
        }
        lvl = lvl - 1
    }

    let candidate = sl["nodes"][curr_idx]["forward"][0]
    if candidate != -1 and sl["nodes"][candidate]["key"] == target_key {
        return sl["nodes"][candidate]["val"]
    }

    return nil
}

pub fn skip_list_insert(sl, key, val, forced_level) {
    let update = dict()
    let curr_idx = 0
    let lvl = sl["max_level"] - 1

    while lvl >= 0 {
        let done = false
        while not done {
            let next_idx = sl["nodes"][curr_idx]["forward"][lvl]
            if next_idx != -1 and sl["nodes"][next_idx]["key"] < key {
                curr_idx = next_idx
            } else {
                done = true
            }
        }
        update[lvl] = curr_idx
        lvl = lvl - 1
    }

    let candidate = sl["nodes"][curr_idx]["forward"][0]
    if candidate != -1 and sl["nodes"][candidate]["key"] == key {
        sl["nodes"][candidate]["val"] = val
        return true
    }

    let new_lvl = forced_level
    if new_lvl <= 0 {
        new_lvl = 1
    }
    if new_lvl > sl["max_level"] {
        new_lvl = sl["max_level"]
    }

    if new_lvl > sl["current_level"] {
        let l = sl["current_level"]
        while l < new_lvl {
            update[l] = 0
            l = l + 1
        }
        sl["current_level"] = new_lvl
    }

    let new_node = dict()
    new_node["key"] = key
    new_node["val"] = val
    new_node["forward"] = dict()

    let node_idx = len(sl["nodes"])

    let l = 0
    while l < new_lvl {
        let prev_idx = update[l]
        new_node["forward"][l] = sl["nodes"][prev_idx]["forward"][l]
        sl["nodes"][prev_idx]["forward"][l] = node_idx
        l = l + 1
    }

    while l < sl["max_level"] {
        new_node["forward"][l] = -1
        l = l + 1
    }

    sl["nodes"] = push(sl["nodes"], new_node)
    return true
}

pub fn skip_list_to_list(sl) {
    let res = []
    let curr = sl["nodes"][0]["forward"][0]
    while curr != -1 {
        res = push(res, sl["nodes"][curr]["key"])
        curr = sl["nodes"][curr]["forward"][0]
    }
    return res
}
```

---

## 4. Real-World Engineering Applications

1. **Redis Sorted Sets (`ZSET`)**: Storing sorted gaming leaderboard scores, auction bids, and sliding-window rate limit counters with instant $\mathcal{O}(\log n)$ rank queries.
2. **LSM Storage Engine MemTables (RocksDB / LevelDB)**: Serving as concurrent in-memory write buffers that maintain sorted key order before flushing to immutable SSTables.
3. **High-Frequency Limit Order Books (LOB)**: Managing price-time priority matching engines in electronic exchanges without pause-inducing tree rotations.
4. **Lucene Index Skip Pointers**: Accelerating Boolean query intersections across long inverted index postings lists.

---

## 5. Verification & Testing

Verify syntax and run compiler tests via:

```bash
python -m lateralus_lang check tests/stdlib_skip_list_tutorial.ltl
python -m lateralus_lang check examples/skip_list_tutorial.ltl
pytest tests/test_compiler.py
```
