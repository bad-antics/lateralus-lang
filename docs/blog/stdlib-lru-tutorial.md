# Mastering LRU Caches in Lateralus: Recency Promotion, Deterministic Eviction, and Temporal Locality

Memory is finite, but application workloads continuously ingest new data. Whether caching database query results, deserialized JSON models, compiled template ASTs, or HTTP response payloads, unbounded memory growth inevitably causes Out-Of-Memory (OOM) crashes.

**LRU (Least Recently Used) Caching** exploits the principle of **Temporal Locality**—data accessed recently is overwhelmingly likely to be accessed again soon. When the cache reaches its preconfigured capacity, it deterministically discards the item that has sat unread the longest.

In this tutorial, we implement, analyze, and test an LRU Cache architecture in Lateralus.

---

## 1. Architectural Model: Recency Promotion and Queue Ordering

An LRU cache maintains an ordered sequence of keys:
- **Head (Index 0)**: The **Least Recently Used (LRU)** item—the next candidate for eviction.
- **Tail (Index $N-1$)**: The **Most Recently Used (MRU)** item—the freshest key in the system.

Whenever an item is read (`get`) or updated (`put`):
1. It is extracted from its current position in the ordering queue.
2. It is appended to the tail (promoted to MRU status).

```lateralus
fn lru_promote(keys: list, target_key: string) -> list {
    let mut updated = [];
    let mut i = 0;
    while i < len(keys) {
        let k = keys[i];
        if k != target_key {
            updated.append(k);
        }
        i = i + 1;
    }
    updated.append(target_key);
    return updated;
}
```

---

## 2. Eviction State Transitions

When inserting a new key into a saturated cache ($\text{len} == \text{capacity}$):
1. Identify `keys[0]` as the eviction candidate.
2. Remove the key and purge its associated value.
3. Advance the remaining queue elements.
4. Insert the new incoming key as the newest MRU.

```lateralus
fn lru_evict_oldest(keys: list) -> list {
    let mut remaining = [];
    let mut i = 1; // Discard index 0
    while i < len(keys) {
        remaining.append(keys[i]);
        i = i + 1;
    }
    return remaining;
}
```

---

## 3. Real-World Query Caching Scenario

In database query proxies, expensive SQL lookups are cached to avoid repeated disk I/O and query planner CPU overhead.

See `examples/lru_tutorial.ltl` for a runnable demonstration managing active user profile queries, handling cache hits, and cleanly discarding expired cold keys.

---

## 4. End-to-End Verification with Golden Vectors

Our verification suite confirms:
- Initial entry insertion up to capacity.
- Read promotion ensuring accessed keys are rescued from eviction.
- Saturated eviction correctly ejecting the historical oldest key.
- Cascading evictions under sequential write bursts.

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/lru_tutorial.ltl
python -m lateralus_lang check tests/stdlib_lru_tutorial.ltl
pytest tests/test_compiler.py
```
