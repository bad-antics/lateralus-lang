# Consistent Hashing with `stdlib/consistent_hash.ltl`

`stdlib/consistent_hash.ltl` implements the classic consistent-hash
ring: each node contributes `vnodes_per_node` virtual points onto a
32-bit hash ring, and every lookup binary-searches for the first
point clockwise of the key's hash. When a node leaves, only the keys
in *its* arcs move — that's the whole point of consistent hashing
for distributed caches and sharding.

Companion: `examples/chash_tutorial.ltl`.

---

## The ring

```text
hash space: 0 ────────────────────────────► 2^32-1
points:     [h, node] sorted ascending; lookup wraps at the end
```

- **`hash_point(node, replica)`** = `fnv1a_64(node + "#" + replica)
  & 0xffffffff` — each replica is a distinct point, so one physical
  node owns several arcs (virtual nodes / replicas).
- **`insort`** keeps `points` sorted by hash (insertion sort — fine
  at tutorial scale).
- **`lookup(r, key)`** binary-searches the first point `>= h(key)`;
  if none exists it wraps to index 0. Empty ring → `""`.
- **`lookup_n(r, key, n)`** walks clockwise collecting *distinct*
  node names — the replica-owner list for read repair or N-copy
  storage.
- **`add_node` / `remove_node`** maintain `nodes` + `points`
  together; removal filters by name, so all its arcs vanish at once.

## Verified results

Ring: 3 nodes × 4 vnodes = 12 points, sorted by hash.

```text
sess-0000-x -> db-2      sess-0004-x -> cache-1     sess-0010-x -> web-1
user:1     -> web-1      order:99   -> web-1
lookup_n(user:1, 3) -> [web-1, cache-1, db-2]   (full clockwise walk)
100 sess-* keys distribute 43 / 37 / 20 across cache-1 / web-1 / db-2
remove web-1: its 37 keys all remap, 0 remain on web-1;
              user:1 moves web-1 -> cache-1 (next clockwise vnode)
```

`tests/test_chash_tutorial.py` pins all of the above.

## ⚠️ Things the tutorial had to work around (and one real insight)

1. **`import hash` doesn't resolve** under `ltlc run` — FNV-1a/64
   inlined (offset `14695981039346656037`, prime `1099511628211`).
2. **Float division**: `mid = (lo + hi) / 2` → float index →
   `TypeError`; `int(...)` workaround — fifth confirmed instance of
   the `/`-is-float family.
3. **Honest caveat — distribution depends on hash avalanche.** Plain
   FNV-1a has weak avalanche: `node#0..#3` replicas hash within a few
   hundred of each other, so each node owns one *tight cluster*, and
   sequential keys (`key-0…key-49`) can all land on one node. Node
   names were chosen (`cache-1`, `web-1`, `db-2`) so clusters spread
   across the ring — a reminder that production rings typically add
   a finalizer mix (e.g. splitmix64-style `h ^= h >> 33`) or use
   more vnodes. Worth a doc note upstream.

## When to use it

**Use it** for consistent-shard key→node mapping, cache replica
selection (`lookup_n`), and as a clean binary-search-on-a-ring
example.

**Don't expect** bounded-load balancing, rendezvous hashing, or
virtual-node *weights* — every vnode counts equally.

That is `stdlib/consistent_hash.ltl`: a 100-line ring that moves
only the keys it must when the cluster changes shape.
