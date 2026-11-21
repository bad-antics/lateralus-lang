# Object Pools with `stdlib/pool.ltl`

When objects are expensive to create and cheap to reuse — database
connections, thread workers, buffers, DOM nodes — you don't allocate
and free them per use. You keep a **pool**: checked-out objects live in
`in_use`, idle ones in `available`, and `acquire`/`release` move them
between the two lists.

`stdlib/pool.ltl` implements the pattern in about 160 lines of pure
map-and-list code. This tutorial covers the LIFO discipline, size caps,
bulk operations, and the stats surface. Companion:
`examples/pool_tutorial.ltl`.

---

## The model

```text
pool = { "available": list, "in_use": list,
         "max_size": int,       -- 0 = unlimited
         "total_created": int }
```

- `available` — idle objects, ready to hand out
- `in_use` — checked-out objects
- `max_size` — ceiling on `available + in_use` (0 disables the cap)
- `total_created` — ever-added count (for leak/usage telemetry)

## Acquire: LIFO, not FIFO

`acquire` pops from the **end** of `available` — a stack discipline.
That's deliberate: the most-recently-released object is the most likely
to still be warm in cache. The tutorial demonstrates it directly:
`from_list([10,20,30])` hands out `30` then `20`, and a `release(20)`
followed by `acquire` returns `20` again — not `10`.

When `available` is empty, `acquire` returns `[pool, nil]` — pools don't
create on demand (that's `add`'s job); exhaustion is a signal, not an
error.

## Release and the size cap

`release` removes the object from `in_use` (first match — duplicates
aren't tracked) and appends it to `available`, **unless** the pool is
at `max_size`, in which case the object is dropped. That guard is what
lets a pool shrink under pressure instead of growing forever.

`add` enforces the same ceiling from the other side: it rejects new
objects when `available + in_use >= max_size`. The tutorial shows a
`max_size=3` pool rejecting a fourth `add` while full, then accepting
acquisitions normally.

## Bulk and lifecycle ops

| Function | Behavior |
|---|---|
| `acquire_many(pool, n)` | n acquisitions; short pool yields `nil` entries |
| `release_all(pool)` | everything in_use → available |
| `drain(pool)` | returns all objects, empties the pool |
| `shrink(pool, n)` | truncates `available` to n entries |
| `stats(pool)` | counts + max + total_created snapshot |

`drain` order is `available ++ in_use` — the tutorial's `[30, 20, 10]`
output shows in_use objects trailing available ones.

## When pooling actually pays

**Use it** for expensive reusable resources: connections, threads,
compiled regexes, buffers. The win is skipping construction cost on the
hot path — acquire/release is two list operations.

**Don't pool** cheap objects (ints, small strings) — the bookkeeping
overlaps the allocation it saves. And note this pool stores *values*,
not raw memory: perfect for object reuse in application code, not a
malloc replacement (that's `stdlib/arena.ltl` / `stdlib/mem.ltl`
territory).

## Running the companion

```text
STEP 1 acquire -> 30 (LIFO: last available first)
STEP 1 acquire -> 20
STEP 1 stats: avail=1 in_use=2 total=3 max=0 created=3
STEP 2 release(20) then acquire -> 20 (most-recently-released wins)
STEP 3 max_size=3, add x3 -> avail=3 in_use=0 total=3 max=3 created=3
STEP 3 add conn-D at max -> avail=3 in_use=0 total=3 max=3 created=3 (rejected)
STEP 3 acquire -> conn-C, stats: avail=2 in_use=1 total=3 max=3 created=3
STEP 4 acquire_many(5) -> [10, None, None, None, None]
STEP 4 stats: avail=0 in_use=3 total=3 max=0 created=3 is_empty=True
STEP 5 release_all -> avail=3 in_use=0 total=3 max=0 created=3
STEP 5 drain -> [30, 20, 10] then stats: avail=0 in_use=0 total=0 max=0 created=3
STEP 6 shrink to 2 -> avail=2 created=4
PINNED_VECTORS: lifo=30,20 reuse=20 max3_add4_rejected drain=30,20,10 shrink_avail=2
```

`tests/test_pool_tutorial.py` pins the transcript — including the nil
padding in `acquire_many` and the LIFO reuse order, the two behaviors
most likely to be got subtly wrong.

That is `stdlib/pool.ltl`: two lists, a ceiling, and the oldest
performance trick there is.
