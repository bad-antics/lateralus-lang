# Building In-Memory Caches with `stdlib/lru.ltl`

> Author: David Telles (@Booshdag-io)  
> Module: `stdlib/lru.ltl`  
> Target: Lateralus v3.2.0+

---

## 1. Introduction

In high-throughput services, repeated lookups to disk, network APIs, or database backends introduce latency spikes and resource contention. An in-memory cache mitigates this by retaining frequently accessed data. However, unbound memory growth inevitably leads to exhaustion.

The **Least Recently Used (LRU)** eviction strategy provides an optimal balance: it bounds maximum memory consumption to a fixed capacity $N$, evicting the least recently accessed item whenever a new entry arrives at full capacity.

Lateralus ships with a native, zero-dependency LRU cache in `stdlib/lru.ltl`. This tutorial walks through its architecture, API surface, deterministic eviction mechanics, and metrics collection.

---

## 2. Architecture & Data Model

In `stdlib/lru.ltl`, the cache is modeled as an immutable/persistent-friendly map containing five core fields:

```ltl
// Cache State representation:
// {
//     "data": map[str -> any],     // Key-value store
//     "order": list[str],          // Recency list (oldest at index 0, newest at end)
//     "capacity": int,             // Maximum allowed items
//     "hits": int,                 // Successful lookups counter
//     "misses": int                // Failed lookups counter
// }
```

- **Data Store (`data`)**: Key-value mapping of current entries.
- **Recency Queue (`order`)**: Chronological index sequence. The element at `order[0]` is the least recently used candidate for eviction. Whenever an entry is read or updated, it moves to `order[len(order) - 1]`.
- **Telemetry Counters (`hits`, `misses`)**: Monotonically increasing counters tracking lookup efficiency.

---

## 3. Initialization

### Creating an Empty Cache
```ltl
import lru

let cache = lru.new(100) // Creates a cache with capacity 100
```

### Initializing from Existing Pairs
```ltl
let initial_data = [
    ["session:1", "user_alpha"],
    ["session:2", "user_beta"]
]
let cache = lru.from_pairs(initial_data, 50)
```
If the pairs exceed the specified capacity, older pairs are automatically evicted in insertion order until capacity is satisfied.

---

## 4. Cache Mutation & Eviction Semantics

### Inserting Data (`lru.put`)
```ltl
cache = lru.put(cache, "api:rate:10.0.0.1", 42)
```
1. If the key already exists: its value is updated, and it is promoted to the most-recently-used position.
2. If the key is new and `len(order) >= capacity`: `order[0]` (the least recently used key) is evicted from `data`, and the new key is appended to the tail.

### Retrieving Data (`lru.get`)
Because Lateralus functions avoid hidden mutable side-effects, `lru.get` returns a 2-tuple: `[updated_cache, value]`.
```ltl
let result = lru.get(cache, "api:rate:10.0.0.1")
cache = result[0]
let value = result[1] // nil if missed
```
- On **Hit**: `hits` increments by 1, and the key moves to the tail of `order`.
- On **Miss**: `misses` increments by 1, and `value` is `nil`.

### Checking Key Existence (`lru.has`)
To check for membership without updating the recency queue:
```ltl
if lru.has(cache, "api:rate:10.0.0.1") {
    print("Key is currently cached")
}
```

---

## 5. Metrics & Telemetry

Production services require real-time cache efficiency observability:

```ltl
let total_hits   = lru.hits(cache)      // int
let total_misses = lru.misses(cache)    // int
let ratio        = lru.hit_rate(cache)  // float in range [0.0, 1.0]
let summary      = lru.stats(cache)     // map containing size, capacity, hits, misses, hit_rate
```

The hit rate formula:
$$\text{Hit Rate} = \frac{\text{Hits}}{\text{Hits} + \text{Misses}}$$
If no queries have occurred, `hit_rate()` safely returns `0.0` avoiding division by zero.

---

## 6. Dynamic Capacity Scaling (`lru.resize`)

Workload demands fluctuate. `lru.resize` allows adapting cache size at runtime:
```ltl
// Expand capacity:
cache = lru.resize(cache, 200)

// Shrink capacity (automatically drains oldest entries until size <= new_capacity):
cache = lru.resize(cache, 50)
```

---

## 7. Runnable Example (`examples/lru_tutorial.ltl`)

Run the complete example with the Lateralus CLI:
```bash
python -m lateralus_lang run examples/lru_tutorial.ltl
```

Expected output:
```text
=== LATERALUS STDLIB LRU TUTORIAL ===
STEP 1: Initialized LRU cache capacity=3, size=0
STEP 2: Inserted 3 items. Cache size=3
STEP 3: Accessed user:1 -> value=Alice (hits=1, misses=0)
STEP 4: Inserted user:4 -> user:2 evicted: has_user2=False, has_user1=True
STEP 5: Querying evicted key -> val=None (hits=1, misses=1)
STEP 6: Resized cache to capacity=2 -> current_size=2
PINNED_VECTORS: hits=1 misses=1 final_size=2
```

---

## 8. Verification & Pinned Test Vectors

The test suite in `tests/test_lru_tutorial.py` validates the deterministic state machine:

| Stage | Operation | Expected State | Pinned Metric |
| :--- | :--- | :--- | :--- |
| **T0** | `lru.new(3)` | `order = []` | `size = 0, cap = 3` |
| **T1** | Insert `user:1, 2, 3` | `order = [user:1, user:2, user:3]` | `size = 3, is_full = true` |
| **T2** | `lru.get(user:1)` | `order = [user:2, user:3, user:1]` | `hits = 1, misses = 0` |
| **T3** | Insert `user:4` | `order = [user:3, user:1, user:4]` | `user:2 evicted` |
| **T4** | `lru.get(user:2)` | `val = nil` | `hits = 1, misses = 1` |
| **T5** | `lru.resize(2)` | `order = [user:1, user:4]` | `user:3 evicted, size = 2` |

All assertions pass under `pytest tests/test_lru_tutorial.py`.
