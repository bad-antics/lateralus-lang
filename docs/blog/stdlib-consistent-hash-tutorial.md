# Mastering Consistent Hashing in Lateralus: Ring Topologies, Virtual Nodes, and Resilient Sharding

In distributed architectures—such as Redis clusters, Apache Cassandra, Amazon DynamoDB, and edge reverse proxies—distributing keys across $N$ storage nodes using naive modular arithmetic:

$$\text{Node} = \text{hash}(\text{key}) \pmod{N}$$

causes catastrophic failure when nodes join or leave. Changing $N$ to $N+1$ invalidates nearly $100\%$ of existing keys, wiping out caches and hammering downstream primary databases (the classic **Cache Avalanche**).

**Consistent Hashing** (pioneered by Karger et al.) solves this by mapping both servers and data keys onto a continuous circular hash ring. When a server is added or removed, only $1/N$ of keys migrate, providing smooth, fault-tolerant elasticity.

In this tutorial, we implement, analyze, and test a Consistent Hash Ring with virtual node support natively in Lateralus.

---

## 1. Architectural Topology: The Circular Continuum

The hash ring wraps modular values along a circular domain from $0$ to a maximum upper bound (typically $2^{32}-1$):

```
                     0 / 2^32
                     [Node A]
                 . - ~ ~ ~ - .
             .                   .
          .                         .
     [Node C]                     [Node B]
       .                             .
        .                           .
          .                       .
             .                 .
                 . - ~ ~ ~ - .
```

- Each physical shard is placed onto the ring at its hash offset.
- Incoming keys are hashed into the same space.
- The coordinator walks clockwise around the ring, assigning the key to the first server encountered whose position is $\ge \text{hash}(\text{key})$.
- If the key's hash exceeds the highest server position, it naturally wraps around to index 0 (the first node).

---

## 2. Virtual Nodes (VNodes) for Skew Mitigation

When a cluster has few physical servers (e.g. 3 nodes), non-uniform hash distributions can assign disproportionate ring segments to a single machine.

By hashing each physical machine across multiple virtual replica identities (e.g., `shard-1#1`, `shard-1#2`, `shard-1#3`), servers interleave evenly across the circumference, achieving near-perfect load balance with zero hot-spot clustering.

```lateralus
fn ring_dispatch(sorted_hashes: list, node_names: list, key_hash: int) -> string {
    let count = len(sorted_hashes);
    if count == 0 {
        return "";
    }
    let mut i = 0;
    while i < count {
        let h = sorted_hashes[i];
        if h >= key_hash {
            return node_names[i];
        }
        i = i + 1;
    }
    // Clockwise wraparound to the first server on the ring
    return node_names[0];
}
```

---

## 3. Real-World Sharding Scenario

Consider an application routing user sessions and cart items across geographical shards (`shard-us-east`, `shard-eu-west`, `shard-ap-south`).

See `examples/consistent_hash_tutorial.ltl` for a runnable demonstration routing high-throughput request keys without linear cluster scans.

---

## 4. End-to-End Verification with Golden Vectors

Our verification suite confirms:
- Exact clockwise server selection.
- Circular wraparound handling for keys exceeding the highest boundary node.
- Deterministic key-to-node routing consistency.

Run the compiler checks and test suites:
```bash
python -m lateralus_lang check examples/consistent_hash_tutorial.ltl
python -m lateralus_lang check tests/stdlib_consistent_hash_tutorial.ltl
pytest tests/test_compiler.py
```
