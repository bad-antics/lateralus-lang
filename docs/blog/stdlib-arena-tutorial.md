# Region Allocation with `stdlib/arena.ltl`

Arena (region-based) allocation is the oldest trick in the book: instead
of freeing each object individually, you allocate everything from one
region and release it all at once. Games do it per-frame, compilers do
it per-function, parsers do it per-document — `stdlib/arena.ltl`
implements the pattern in about 160 lines using nothing but maps and
lists.

This tutorial covers the block-chunked layout, slot-id addressing,
`alloc_many`, the stats surface, and the O(1) `reset` that makes arenas
worth it. Companion: `examples/arena_tutorial.ltl`.

---

## The layout: blocks of slots

An arena is a map:

```text
{ "blocks": list of lists, "current": int, "capacity": int, "total": int }
```

`new(capacity)` starts with one empty block. `alloc` appends to the
current block; when it reaches `capacity`, a fresh block is appended and
becomes current. So memory grows in chunks — you never realloc, you
just grab the next slot.

## Slot ids: flat addressing across blocks

Every allocation returns `[arena, id]` where `id = block_index *
capacity + slot_index` — a single flat integer that encodes both where
the value lives and its position. `get`/`set` decode it:

```text
block_idx = id / capacity      (integer division)
slot_idx  = id % capacity
```

Flat ids are what make arenas scriptable: a compiler can hand out ids
during parsing and resolve them in a second pass without keeping object
references alive.

> **Portability note:** the module writes `id / capacity` directly as an
> index. Under the Python backend `/` yields a float, which can't index
> a list — the companion uses `int(id / capacity)`. Worth knowing if you
> port arena-style code.

## The API surface

| Function | Purpose |
|---|---|
| `new(cap)` / `default()` | create arena (default block = 1024 slots) |
| `alloc(arena, v)` | allocate one value → `[arena, id]` |
| `alloc_many(arena, vs)` | batch-allocate → `[arena, [ids]]` |
| `get` / `set` | read/write by slot id (out-of-range → `nil`) |
| `total` / `block_count` | live allocation count / blocks in use |
| `remaining` / `total_capacity` / `usage` | capacity telemetry |
| `reset` | drop everything, O(1) |
| `to_list` / `stats` | flatten live values / snapshot metrics |

## Why reset is the whole point

`reset` doesn't free anything — it just resets `blocks` to `[[]]`,
`current` to 0, `total` to 0. Every slot id from before the reset is
dead (`get` returns `nil`), and the next `alloc` reuses slot 0.

That's the arena contract: **allocations are cheap, deallocation is
free, and individual frees don't exist.** If your objects have
incompatible lifetimes, an arena is the wrong tool — but if they all
die together (a frame's geometry, a request's AST, a parse's tokens),
you get malloc-fast allocation and instant teardown.

## Running the companion

```text
STEP 1 ids: 0,1,2 (capacity 3 fills block 0)
STEP 1 4th alloc -> id 3 (spills to block 1)
STEP 2 after set: get(id2) = BETA
STEP 3 alloc_many ids = [4,5,6] total=7
STEP 3 to_list = [alpha, BETA, gamma, delta, x, y, z]
STEP 4 stats: total=7 blocks=3 cap=9 remaining=2 usage=0.7777777777777778
STEP 5 after reset: total=0 blocks=1 get(old id1)=None
PINNED_VECTORS: ids=0,1,2,3 spill=block1 set=BETA many=4,5,6 total=7 blocks=3 usage=0.7777777777777778 reset_total=0
```

`tests/test_arena_tutorial.py` pins the transcript — the id arithmetic
(`0,1,2` then spill to `3`), the `set` overwrite, `alloc_many`'s
`[4,5,6]` ids, and the post-reset `nil` are all regression-covered.

## When to use it

**Use it** for batch-lifetime data: per-frame game state, per-request
parse trees, per-job scratch space, anything where "free everything at
once" matches your actual lifetime structure.

**Don't use it** when objects have mixed lifetimes — you'd leak the
long-lived ones until reset. And remember this is a *logical* arena
(values in lists, not raw memory): great for teaching the pattern and
managing object graphs, not a replacement for `malloc`-level control.
For real systems work, `stdlib/mem.ltl` + `stdlib/ptr.ltl` are the
raw-memory layer.

That is `stdlib/arena.ltl`: chunked blocks, flat slot ids, and a reset
button that makes deallocation a non-event.
