# Lazy Iterators with `stdlib/iter.ltl`

Most languages give you iterators that are *lazy* — `map`, `filter`,
and `take` produce new iterators without touching the data until a
terminal operation asks for values. `stdlib/iter.ltl` implements that
same shape in about 290 lines: every function is pure, every stage
returns a fresh iterator, and nothing is evaluated until you call a
terminal.

This tutorial covers iterator construction, the chainable transforms,
the terminal operations, and the three representation details that
surprise people the first time. Companion:
`examples/iter_tutorial.ltl`.

---

## An iterator is just a tagged map

There is no iterator class. `from_list` wraps a list in a map:

```ltl
{"_type": "iter", "source": lst, "index": 0,
 "transforms": [], "len": len(lst)}
```

`_type` is the discriminator — `collect` throws `TypeError` if you
hand it anything else. `transforms` is reserved for a future fused
pipeline; today every combinator *eagerly* collects and rebuilds, so
the laziness is in the API shape, not in deferred execution. That is
worth knowing before you reach for `iter` on a million-element list:
it will allocate the intermediate list at every stage.

## Construction

```ltl
range_iter(1, 6)        // [1,2,3,4,5]   — stop-exclusive
range_step(0, 10, 3)    // [0,3,6,9]     — positive step
range_step(9, 0, -3)    // [9,6,3]       — negative step counts down
repeat(7, 3)            // [7,7,7]
once(42)                // [42]
empty()                 // []
from_list([3,1,3,2,1,3])// wrap an existing list
```

`range_iter` is stop-exclusive like Python's `range`, and
`range_step` is the only constructor that accepts a stride — it
dispatches on the sign of `step`, so `range_step(9, 0, -3)` walks
downward.

## Transforms: each stage returns a new iterator

Every transform calls `collect` on its input and returns
`from_list(result)` — so stages can be chained freely:

```ltl
let base     = range_iter(1, 11)                          // 1..10
let doubled  = iter_map(base, fn(x) { return x * 2 })     // 2,4,..20
let evens    = iter_filter(doubled, fn(x) { return x % 4 == 0 })
// evens collects to [4, 8, 12, 16, 20]
```

The full transform set:

| Function | Effect |
|---|---|
| `iter_map` / `iter_filter` | element-wise transform / predicate keep |
| `iter_take(n)` / `iter_skip(n)` | prefix / suffix by count |
| `iter_take_while(pred)` / `iter_skip_while(pred)` | prefix/suffix by predicate |
| `iter_flat_map(f)` | `f` returns a **list**, results concatenated |
| `iter_enumerate` | wraps each item as `{index, value}` |
| `iter_zip(a, b)` | pairs items, stops at the shorter side |
| `iter_chain(a, b)` | concatenates two iterators |
| `iter_unique` | first-occurrence dedup via `to_str` keys |
| `iter_chunks(n)` / `iter_windows(n)` | list-of-lists batching / sliding window |

Two sharp edges worth pinning down:

- **`iter_flat_map` wants a list back, not an iterator.** The module
  does `for y in sub`; if `sub` is an iterator *map*, `for` walks its
  keys (`_type`, `source`, …) instead of values. Pass
  `fn(x) { return [x*x] }`, or `collect(...)` an inner iterator
  first.
- **`iter_unique` keys on `to_str(x)`**, so `1` and `"1"` collide —
  and mixed-type dedup keeps the *first* occurrence's original value.

## Terminal operations

Terminals consume the iterator and return plain data:

```ltl
collect(it)                 // the underlying list
iter_reduce(it, init, f)    // left fold; iter_fold is an alias
iter_sum / iter_product     // numeric folds (return float)
iter_count                  // len(collect(it))
iter_any / iter_all         // existential / universal predicate
iter_find(pred)             // {"_tag":"Some","value":x,...} or None-map
iter_position(pred)        // index of first match, -1 if none
iter_min / iter_max         // throw ValueError on empty
iter_for_each(it, f)        // run f for side effects, returns nothing
iter_to_map(key_fn, val_fn) // build a map from two projections
```

`iter_find` does not return the value or `nil` — it returns a tagged
map so callers can distinguish "found `false`" from "not found":

```ltl
let hit = iter_find(range_iter(1, 11), fn(x) { return x % 2 == 0 && x > 6 })
// {'_tag': 'Some', 'value': 8, 'is_some': True}
```

## Lambda scoping gotcha

`iter_for_each` is the only terminal that exists for side effects,
and its callback **cannot rebind an outer `let mut` variable** — the
Python backend compiles lambdas as closures, so `seen = push(seen, x)`
inside `fn(x) { ... }` raises `UnboundLocalError`. Mutating a *map*
works fine because maps are reference types:

```ltl
let acc = {}
acc["total"] = 0
iter_for_each(range_iter(1, 4), fn(x) { acc["total"] = acc["total"] + x * x })
// acc["total"] == 14   (1+4+9)
```

## Pinned test vectors

The companion example prints a `PINNED_VECTORS` line that
`tests/test_iter_tutorial.py` asserts byte-for-byte:

```
sum(1..10) = 55          product(1..5) = 120
chunks(1..7, size 3) = 3 windows(1..5, size 3) = 3
unique([3,1,3,2,1,3]) = [3,1,2]   (length 3)
zip stops at shorter side          (min length 2)
```

If a future change to `stdlib/iter.ltl` alters any of these, the
test fails — that is the point of pinning them.

## Try it

```bash
python3 -m lateralus_lang run examples/iter_tutorial.ltl
python3 -m pytest tests/test_iter_tutorial.py -q
```

The module itself lives at `stdlib/iter.ltl`; every function in this
tutorial is inlined verbatim into the example (with the two documented
adjustments: imperative map construction and the `contains(keys(...))`
membership check), so the example runs on any backend without needing
module resolution.
