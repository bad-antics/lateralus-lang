# Binary Min-Heap with `stdlib/heap.ltl`

`stdlib/heap.ltl` is a textbook binary min-heap stored as a flat
list: parent at `(i-1)/2`, children at `2i+1` / `2i+2`. Every
operation is O(log n) except `peek`/`size`/`is_empty` which are
O(1). On top of the core sift operations it provides the usual
priority-queue conveniences — `push_pop`, `replace`,
`n_smallest`, `merge` — plus `heap_sort`, which is just "pop until
empty" and yields sorted output for free.

Companion: `examples/heap_tutorial.ltl`.

---

## The array layout

```text
        0
      /   \
     1     2
    / \   / \
   3   4 5   6
```

The heap invariant — every parent ≤ its children — is maintained by
two sifts:

- **`_sift_up(h, i)`** — after appending at the end, swap with the
  parent while the child is smaller. Used by `push`/`from_list`.
- **`_sift_down(h, i)`** — replace the root, then repeatedly swap
  with the *smaller* child until the invariant holds. Used by
  `pop`/`push_pop`/`replace`.

## API walkthrough

| Function | Returns | Notes |
|---|---|---|
| `new()` / `from_list(items)` | heap | `from_list` inserts one-by-one (O(n log n), not Floyd's O(n)) |
| `push(h, v)` | new heap | append + sift_up |
| `pop(h)` | `[min, new_heap]` | move last to root + sift_down |
| `peek(h)` | min or `nil` | O(1), no removal |
| `push_pop(h, v)` | `[popped, heap]` | if `v <= root`, `v` becomes the min — clever shortcut |
| `replace(h, v)` | `[old_min, heap]` | overwrite root + sift_down |
| `n_smallest(h, n)` | sorted list | repeated `pop`, capped at heap size |
| `merge(h1, h2)` | heap | push every element of h2 into h1 |
| `heap_sort(items)` | sorted list | build heap then pop all |

## Verified results

```text
hfrom([5,2,8,1,9,3]) -> heap array [1,2,3,5,9,8], peek=1
pop order -> 1,2,3,5,8,9            (sorted extraction)
push_pop([10,20,30], 5)  -> popped=5,  heap0=10
push_pop([10,20,30], 99) -> popped=10
replace([4,8,15], 1)     -> old_min=4, new peek=1
n_smallest([42,7,13,99,23,1], 3) -> [1,7,13]
merge([1,5],[3,2]) -> size 4, peek 1
heap_sort([9,4,7,1,3]) -> [1,3,4,7,9]
```

`tests/test_heap_tutorial.py` pins every value.

## ⚠️ Upstream bug found (worked around)

`_parent` computes `(i - 1) / 2`. Under the current Python runtime
shim `/` is **float division**, so `_parent(1)` returns `0.0` and
`h[p]` raises `TypeError: list indices must be integers or slices,
not float` — meaning **`push`/`from_list`/`heap_sort` are broken
upstream** the first time a sift actually climbs. The tutorial uses
`int((i - 1) / 2)`. Same float-division family as the `ldap.enc_len`
and `totp._u64_be` bugs — now a pattern worth a dedicated fix pass
(`grep -n ') / ' stdlib/*.ltl` will find the rest).

## When to use it

**Use it** for k-smallest/k-largest queries (`n_smallest`), merge
of priority queues, online sorting, Dijkstra/A* frontier queues,
and job schedulers where the min (or negated max) must stay on top.

**Don't expect** a max-heap (negate values), decrease-key, or
stable ordering — equal elements pop in arbitrary heap order.
Also note `from_list` is insertion-based O(n log n); a Floyd
bottom-up heapify would be O(n) if this ever gets perf attention.

That is `stdlib/heap.ltl`: forty lines of sifting that give you a
priority queue, a partial sorter, and a sorting algorithm in one.
