# Sets Without Hash Tables: `stdlib/set.ltl` in Practice

Most languages give you a `Set` backed by a hash table — O(1) membership,
unordered iteration, and a healthy dose of "why is my iteration order
random?". Lateralus takes a different, more transparent route:
`stdlib/set.ltl` represents a set as a **sorted, deduplicated list**.

That design choice is the whole tutorial. Sorted lists make membership a
binary-search-shaped problem, make every set operation a `filter`/`map`
away, and — crucially — make set behaviour **fully deterministic and
debuggable**: two equal sets are always the same list, so `equals` is just
subset-in-both-directions and `to_list` needs no canonicalisation pass.

The companion script `examples/set_tutorial.ltl` exercises every public
function on two small sets with pinned output; `tests/test_set_tutorial.py`
locks the transcript in CI.

---

## The representation

```text
set := sorted list with no duplicates
```

Construction is `from_list(items)`: scan the input, keep elements not
already present (`contains`), then `sort` the survivors. Add is the same
idea — insert only if absent, re-sort, return the new list.

Because the representation is canonical, the predicates get trivial:

- `has(s, item)` → `contains(s, item)`
- `size(s)` → `len(s)`
- `is_empty(s)` → `len(s) == 0`
- `equals(a, b)` → same length **and** `is_subset(a, b)`

## The four set operations

Given `A = {1,2,3,4}` and `B = {3,4,5,6}`:

| Operation | Result | Implementation |
|---|---|---|
| `union(A, B)` | `[1,2,3,4,5,6]` | copy `a`, append unseen `b` items, sort |
| `intersection(A, B)` | `[3,4]` | `a \|> filter(contains(b, ·))` |
| `difference(A, B)` | `[1,2]` | `a \|> filter(!contains(b, ·))` |
| `symmetric_difference(A, B)` | `[1,2,5,6]` | `difference` both ways, merge, sort |

Intersection and difference are single `filter` passes — O(|a|·|b|) worst
case because `contains` is a linear scan. That is the honest cost of the
sorted-list design: membership is O(n), not O(1). For the tag sets,
dedup lists, and ID collections this module is built for, n is small and
the clarity win is large.

## The predicates

```text
is_subset(a, b)      — every element of a appears in b
is_superset(a, b)    — is_subset(b, a), literally
is_disjoint(a, b)    — intersection is empty
equals(a, b)         — same size and mutual subset
```

Note `equals` exploits canonicity: since both sets are sorted and
deduplicated, subset-in-one-direction plus equal length is sufficient —
no element-by-element comparison needed.

## Higher-order helpers

- `map_set(s, f)` — apply `f` to every element and re-canonicalise via
  `from_list`. Duplicates created by the mapping collapse automatically —
  `map_set({1,2,3}, x -> x % 2)` yields `{0, 1}`, not `{0,1,0,1,0,1}`.
- `filter_set(s, pred)` — keep elements matching `pred`; already canonical.
- `fold(s, init, f)` — reduce over elements in sorted order, so fold
  results are deterministic regardless of insertion history.
- `power_set(s)` — all `2^|s|` subsets. Built recursively: take the power
  set of the tail, then prepend the head to each subset. For `s = {1,2}`
  the module returns `[[], [2], [1], [1, 2]]` — note the ordering is an
  implementation detail, not sorted-by-size; if you need canonical order,
  `sort` the outer list yourself.

## Running the companion script

```text
$ lateralus run examples/sort_tutorial.ltl   # (set_tutorial.ltl)
=== LATERALUS STDLIB SET TUTORIAL ===
A = from_list([4,1,3,2,2,4]): [1, 2, 3, 4]
B = from_list([6,3,5,4]): [3, 4, 5, 6]
STEP 2: add(A, 9): [1, 2, 3, 4, 9]
STEP 3: union(A,B): [1, 2, 3, 4, 5, 6]
STEP 4: intersection(A,B): [3, 4]
STEP 5: difference(A,B): [1, 2]
STEP 6: symmetric_difference(A,B): [1, 2, 5, 6]
STEP 7: is_subset([1,2],A) = true
STEP 7b: is_subset(B,A) = false
STEP 8: is_disjoint(A,[7,8]) = true
STEP 8b: is_disjoint(A,B) = false
STEP 9: equals(from_list([4,3,2,1]),A) = true
STEP 10: map_set(A, x*10): [10, 20, 30, 40]
STEP 11: filter_set(A, even): [2, 4]
STEP 12: power_set([1,2]) has 4 subsets
```

## When to use it — and when not to

**Use `stdlib/set.ltl`** when you need set semantics with guaranteed
determinism: small membership lists, config allow/denylists, deduplicating
IDs, teaching set theory. Every operation's result is inspectable — you can
`println` a set and see exactly what's in it.

**Don't use it** when membership tests dominate at scale: `has()` is a
linear scan, so a hot loop over a 100k-element "set" will hurt. For that,
reach for a hash-backed structure or `stdlib/dict_encoding.ltl`'s
encode/decode pairs — the module docs are honest that this is a
clarity-first design, and the O(n) membership cost is the price of
canonical, printable, mergeable sets.

That is `stdlib/set.ltl` end to end: fourteen public functions, one
invariant (sorted + deduplicated), and a companion script that pins every
behaviour so you can verify the module against your own expectations.
