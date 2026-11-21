# Functional List Tools with `stdlib/collections.ltl`

`stdlib/collections.ltl` is the functional-programming shelf of
the stdlib: slicing (`head`/`tail`/`last`/`init`/`take`/`drop`),
concat and search (`concat`, `contains_item`, `index_of_item`),
predicates (`count_where`, `any_match`, `all_match`), transforms
(`flat_map`, `zip_with`), reshaping (`chunk`, `interleave`,
`partition`, `group_by`), higher-order folds (`foldl`, `sum_list`,
`product`), extremes (`max_item`, `min_item`), and
`range_list`/`enumerate_list`. ~185 lines.

Companion: `examples/collections_tutorial.ltl`.

---

## The combinators, grouped

### Slicing — all just `slice`/`len` under the hood

```text
[5,3,8,1,9,2]: head=5 last=2 tail=[3,8,1,9,2] init=[5,3,8,1,9]
               take(2)=[5,3] drop(2)=[8,1,9,2]
```

`head`/`last`/`max_item`/`min_item` throw `IndexError` on empty
input (upstream uses `throw`; the tutorial returns sentinels).

### Search & predicates

`contains_item`, `index_of_item` (−1 when absent), and the three
predicate reducers `count_where`/`any_match`/`all_match` — all take
a function argument, demonstrated with `is_even`/`is_pos`.

### Transforms & reshaping

- `flat_map(lst, f)` — `f` returns a list; results concatenate.
  `double(x)=[x,2x]` on `[1,2,3]` → `[1,2,2,4,3,6]`.
- `chunk(lst, size)` — slices into `size`-length sublists
  (throws on `size <= 0` upstream).
- `interleave(a, b)` — alternates elements, longer list drains.
- `partition(lst, pred)` — returns `[yes, no]` pair.
- `group_by(lst, key_fn)` — map of key → member list.
- `enumerate_list` — `[[0,x],[1,y],…]` index pairs.

### Aggregates

`sum_list`/`product` return **float** (`0.0`/`1.0` seeds) — output
shows `28.0`/`24.0`; `foldl` delegates to `reduce`.

## ⚠️ Upstream bugs found (worked around)

1. **`group_by` crashes on first-seen keys**: `groups[k] == nil`
   evaluates `groups[k]` which raises `KeyError` for missing keys —
   the nil check never gets a chance. Reproduced live. Fix pattern:
   `contains(keys(groups), k)` guard (used in the tutorial; also
   note keys must be strings — the tutorial's `parity` returns
   `"even"`/`"odd"`).
2. **`zip_with` has a syntax-level bug**: `map(pairs, fn(p) p[0] +
   p[1])` — malformed lambda syntax; can't compile as written.
   The tutorial demonstrates the equivalent manually.
3. Higher-order params named `fn` shadow nothing here but read
   oddly; `let mut`, `for`, `throw`, `as float` casts are
   module-file conveniences replaced by `let`/`while`/sentinels in
   the companion.

## Verified results

```text
xs=[5,3,8,1,9,2]: head=5 last=2 tail/init/take/drop all correct
contains 8=T index_of 9=4 ; count_even=2 any_pos=T all_pos=T
flat_map double=[1,2,2,4,3,6]
chunk3=[[5,3,8],[1,9,2]] interleave=[1,2,3,4,5]
partition even: yes=[8,2] no=[5,3,1,9]
group_by parity: even=[2,4,6] odd=[1,3,5]
sum=28.0 product=24.0 max=9 min=1 enumerate=[[0,a],[1,b]]
```

`tests/test_collections_tutorial.py` pins every value.

## When to use it

**Use it** as the "batteries-included" list layer — reach for
`chunk`/`partition`/`group_by` before hand-rolling loops, and for
`flat_map`/`enumerate` in data-munging pipelines.

**Don't expect** `zip_with` to work (see bug #2), lazy/infinite
sequences, or sort/dedup helpers — those live elsewhere or not at
all.

That is `stdlib/collections.ltl`: two dozen small functions that
make list code read like a pipeline.
