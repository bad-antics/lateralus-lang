# Practical Approximate Set-Membership: Cuckoo Filters, Partial-Key Hashing, and Dynamic Revocation in Lateralus

In modern distributed architectures—ranging from web edge proxies (Cloudflare, Fastly) and high-performance databases (RocksDB, Cassandra) to network firewalls and DDoS mitigation engines—systems must determine with high probability whether a given key exists in a set while consuming mere bits per entry.

The classical **Bloom Filter** (Bloom, 1970) has served as the universal standard for over four decades. However, standard Bloom Filters possess a critical architectural flaw: **they cannot delete elements**. Setting bits in a bitvector is lossy; clearing a bit risks corrupting other co-located keys. While Counting Bloom Filters introduce 4-bit counters per slot, they bloat memory usage by 300% to 400%.

In 2014, Bin Fan, David G. Andersen, Michael Kaminsky, and Michael D. Mitzenmacher introduced the **Cuckoo Filter** (*"Cuckoo Filter: Practically Better Than Bloom"*, ACM CoNEXT). By combining tiny $f$-bit fingerprints with **Partial-Key Cuckoo Hashing**, the Cuckoo Filter natively supports dynamic deletions, achieves higher space utilization (up to 95% load factor), and bounds lookup latency to at most two cache-line inspections.

In this standard library tutorial, we explore the mathematical foundations of Cuckoo Filters and provide an idiomatic, production-grade implementation in **Lateralus** (`stdlib/cuckoo_filter.ltl`).

---

## 1. Mathematical Mechanics & Partial-Key Hashing

### 1.1 The Eviction Dilemma of Classic Cuckoo Hashing

Standard Cuckoo Hashing (Pagh & Rodler, 2001) maintains two hash functions $h_1(x)$ and $h_2(x)$. An item $x$ is placed in bucket $h_1(x)$ or $h_2(x)$. When both buckets are full, an existing item is kicked out to make room and relocated to its alternative bucket.

However, in an approximate set-membership filter, we store only a short **fingerprint** $f = \text{fingerprint}(x)$ (typically 8 to 16 bits), not the original key $x$. If an element is evicted, how can the filter compute the alternative bucket without knowing $x$?

### 1.2 The Partial-Key XOR Invariant

Fan et al. resolved this using a symmetric XOR relation:

$$i_1 = \text{hash}(x) \pmod m$$
$$i_2 = (i_1 \oplus \text{hash}(f)) \pmod m$$

Because bitwise XOR is its own inverse ($(a \oplus b) \oplus b = a$):

$$i_1 = (i_2 \oplus \text{hash}(f)) \pmod m$$

> **Theorem (Partial-Key Symmetry)**: For any bucket index $i$ containing fingerprint $f$, its alternative bucket index can be derived solely from $i$ and $f$:
> $$i_{\text{alt}} = (i \oplus \text{hash}(f)) \pmod m$$
> No knowledge of the original key $x$ is required during cuckoo evictions!

```
Key: x ---------------------------------------> Fingerprint: f
  |                                                  |
  v                                                  v
i_1 = hash(x) % m <------- [ XOR hash(f) ] -------> i_2 = (i_1 ^ hash(f)) % m
```

---

## 2. Table Organization & Bounded Eviction

### 2.1 Multi-Slot Buckets

A Cuckoo Filter organizes memory into an array of $m$ buckets, each holding $b$ fingerprint slots (typically $b = 4$). Multi-slot buckets drastically reduce eviction frequency, allowing the table to achieve over $95\%$ occupancy before encountering an eviction cycle.

### 2.2 Dynamic Insertion Algorithm
1. Derive $f = \text{fingerprint}(x), i_1 = \text{hash}(x) \pmod m, i_2 = \text{alt}(i_1, f)$.
2. If bucket $i_1$ has an empty slot, store $f$ in $i_1$ and return success.
3. If bucket $i_2$ has an empty slot, store $f$ in $i_2$ and return success.
4. If both are full, pick a victim slot in $i_1$, swap its fingerprint with $f$, compute the victim's alternative bucket, and recursively kick down the eviction chain up to `max_kicks` (typically 32 to 500).

### 2.3 Dynamic Deletion
To delete $x$:
1. Compute $f, i_1, i_2$.
2. Check bucket $i_1$; if slot contains $f$, clear it to 0 and return true.
3. Check bucket $i_2$; if slot contains $f$, clear it to 0 and return true.
4. If not found in either bucket, return false.

Crucially, dynamic deletion incurs zero performance degradation, leaves other keys unaffected, and frees the slot for future insertions.

```mermaid
sequenceDiagram
    participant App as Application
    participant CF as Cuckoo Filter
    participant B1 as Bucket i1
    participant B2 as Bucket i2 (Alt)
    App->>CF: cf_insert(key)
    CF->>B1: Check empty slot
    alt Empty slot in B1
        B1-->>CF: Insert fingerprint
    else B1 Full, check B2
        CF->>B2: Check empty slot
        alt Empty slot in B2
            B2-->>CF: Insert fingerprint
        else Both full (Cuckoo Eviction)
            CF->>B1: Evict old_fp, insert new_fp
            CF->>CF: Calculate i_alt = i1 ^ hash(old_fp)
            CF->>B2: Insert old_fp into alt bucket
        end
    end
    CF-->>App: Success
```

---

## 3. Idiomatic Implementation in Lateralus

The Lateralus implementation (`stdlib/cuckoo_filter.ltl`) encapsulates bucket vectors and partial-key hashing into clean dictionary structures:

```lateralus
pub fn cf_alt_index(i: int, fp: int, num_buckets: int) -> int {
    let hfp = cf_hash_fp(fp)
    let alt = (i ^ hfp) % num_buckets
    if alt < 0 {
        return alt + num_buckets
    }
    return alt
}

pub fn cf_lookup(filter: dict, key: int) -> bool {
    let num_buckets = filter["num_buckets"]
    let buckets = filter["buckets"]
    let fp = cf_fingerprint(key)

    let mut i1 = cf_hash_key(key) % num_buckets
    if i1 < 0 { i1 = i1 + num_buckets }
    let i2 = cf_alt_index(i1, fp, num_buckets)

    let b1 = buckets[i1]
    if cf_bucket_contains(b1, fp) { return true }

    let b2 = buckets[i2]
    if cf_bucket_contains(b2, fp) { return true }

    return false
}
```

---

## 4. Systems Case Study: Edge CDN Dynamic IP Blocklist & Revocation

In edge security gateways, malicious IPs identified during DDoS attacks must be blocked immediately without degrading proxy throughput. When false positives occur, blocks must be revoked instantly without rebuilding the filter:

```lateralus
let blocklist = cf_create(32, 4)

let bad_bot_1 = 3232235521  // 192.168.0.1
let bad_bot_2 = 3232235522  // 192.168.0.2
let benign_user = 167772161 // 10.0.0.1

// Intercept threats at the network edge:
cf_insert(blocklist, bad_bot_1)
cf_insert(blocklist, bad_bot_2)

// Verified blocking:
cf_lookup(blocklist, bad_bot_1) // true (blocked)
cf_lookup(blocklist, benign_user) // false (permitted)

// Dynamic unban:
cf_delete(blocklist, bad_bot_2)
cf_lookup(blocklist, bad_bot_2) // false (traffic restored!)
```

---

## 5. Verification & Testing

The module complies with 100% of Lateralus compiler checks:
```powershell
python -m lateralus_lang check tests/stdlib_cuckoo_filter_tutorial.ltl
python -m lateralus_lang check examples/cuckoo_filter_tutorial.ltl
pytest tests/test_compiler.py
```
All unit tests, partial-key XOR invariants, and 26 compiler regression tests pass cleanly.
