# Functional Programming with `stdlib/functional.ltl`

`stdlib/functional.ltl` is a 270-line toolkit of composable function
utilities — the Haskell/Elixir/Clojure staples: composition,
currying, higher-order list operations, and small list builders.
Everything is a plain `fn` value you can pass, return, and compose;
there are no classes and no macros.

This tutorial covers composition and pipelines, manual currying,
the higher-order list functions, and the four representation details
that differ from the module's first draft. Companion:
`examples/functional_tutorial.ltl`.

---

## Composition: functions are values

`compose(f, g)` returns a new function — note the argument order,
`compose(dbl, inc)(5)` computes `dbl(inc(5)) = 12`, i.e. right-to-left
like mathematical composition:

```ltl
let both = compose(dbl, inc)
both(5)   // 12
```

`pipe_fn` is the left-to-right counterpart: it takes a **list** of
functions and threads a value through them in order,
`pipe_fn([inc, dbl, inc])(5) = 13`. `identity`, `constant`, and
`flip` round out the small combinators — `flip(sub)(3, 10)` gives
`sub(10, 3) = 7`.

## Currying by hand

Lateralus has no built-in currying, so the module nests lambdas:

```ltl
let add = fn(a, b) { return a + b }
let add5 = curry2(add)(5)     // fn(b) -> add(5, b)
add5(3)                        // 8

let cat3 = curry3(fn(a,b,c) { return a + b + c })
cat3("x")("y")("z")            // "xyz"

let plus10 = partial(add, 10)  // fixes the FIRST argument only
plus10(7)                      // 17
```

`partial` is the pragmatic one: it binds one argument and leaves a
single-argument function. `curry3` shows the nesting depth grows
fast — past two arguments, `partial` is usually clearer.

## Higher-order list operations

The list half of the module covers the usual suspects:

| Group | Functions |
|---|---|
| Transform | `flat_map`, `scan`, `zip_with` |
| Predicate-driven | `take_while`, `drop_while`, `find`, `find_index`, `every`, `some`, `none_match`, `count_by` |
| Grouping | `group_by`, `partition`, `frequencies` |
| Effects | `for_each` |

```ltl
flat_map([1,2,3], fn(x) { return [x*x] })        // [1,4,9]
scan([1,2,3,4], 0, fn(a,b) { return a+b })       // [0,1,3,6,10]
zip_with([1,2,3],[10,20,30], add)                // [11,22,33]
take_while([1..5], fn(x) { return x < 4 })       // [1,2,3]
drop_while([1..5], fn(x) { return x < 3 })       // [3,4,5]
partition([1..5], is_even)                      // [[2,4],[1,3,5]]
```

Notes on the sharp edges:

- **`zip_with` truncates to the shorter input** —
  `zip_with([1,2,3,4],[10,20], add) = [11,22]`.
- **`group_by` stringifies keys with `to_str`**, so grouping by
  `x % 2` yields `"0"`/`"1"` keys, not ints.
- **`partition` returns `[matching, non_matching]`** — easy to swap
  by accident; the tutorial prints both sides to pin the order.
- **`find` returns `nil` on no match** and does not distinguish
  "found nil" — same caveat as any nil-returning search.

## List builders

`range_list(start, end)` is stop-exclusive, `range_step` takes a
stride, `repeat_val` tiles a value, and `iterate(f, x0, n)` applies
`f` n−1 times — `iterate(inc, 1, 5) = [1,2,3,4,5]`.

## The `for_each` closure gotcha

`for_each` exists for side effects, but a lambda **cannot rebind an
outer `let mut` variable** — the Python backend compiles lambdas as
closures, so `hits = hits + x` inside `fn(x) { ... }` raises
`UnboundLocalError`. Mutate a map instead, since maps are reference
types:

```ltl
let acc = {}
acc["total"] = 0
for_each([1,2,3,4], fn(x) { acc["total"] = acc["total"] + x })
// acc["total"] == 10
```

## Fixes applied while inlining

The tutorial inlines the module verbatim *except* four documented
corrections the current module needs to run on the Python backend:

1. **`push(lst, x)` as a bare statement is a no-op** — it returns a
   new list. Every `push(...)` call site in the module now assigns
   the result (`result = push(result, x)`). As written, `flat_map`,
   `scan`, `group_by`, `partition`, `frequencies`, and the range
   builders all silently return empty/partial results.
2. **`length()` is not a builtin** — `len()` is used instead.
3. **`str()` → `to_str()`** for value-to-string conversion.
4. **`-> nil` is not a valid return annotation** (nil is a value,
   not a type name) — `-> any` is used; and `drop_while`'s empty
   `if` branch was inverted because an empty branch transpiles to
   invalid Python.

These are module bugs, not tutorial license — a future `fix/`
PR against `stdlib/functional.ltl` should apply the same four
changes upstream.

## Pinned test vectors

`PINNED_VECTORS: compose=12 pipe=13 zipmin=33 group_n=2 freq_a=3
scan=[0,1,3,6,10]` is asserted byte-for-byte by
`tests/test_functional_tutorial.py`.

## Try it

```bash
python3 -m lateralus_lang run examples/functional_tutorial.ltl
python3 -m pytest tests/test_functional_tutorial.py -q
```
