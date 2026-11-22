# Foundational Helpers with `stdlib/core.ltl`

`stdlib/core.ltl` is the module every Lateralus program implicitly
leans on: `print`/`println`, `assert`, numeric helpers (`abs`,
`clamp`, `min`, `max`), conversions (`to_str`, `len`), and the
functional trio (`repeat`, `map`, `filter`, `reduce`, `sum`,
`range`). ~110 lines — the "prelude" of the standard library.

Companion: `examples/core_tutorial.ltl`.

---

## Numeric helpers — trivially correct

```text
abs(-3.5)=3.5   clamp(5,0,10)=5.0   clamp(-1,0,10)=0.0   clamp(99,0,10)=10.0
min(3,7)=3.0    max(3,7)=7.0
```

All return **float** (`float` signatures) — outputs show `5.0`,
`3.0`. `clamp` is two comparisons: below `lo` → `lo`, above `hi` →
`hi`, else `x`.

## `repeat(n, body)` — the iteration primitive

Calls `body(i)` for `i` in `0..n-1`. Since Lateralus closures over
mutable state are limited, the tutorial demonstrates the pattern
with a manual counter loop (the upstream version takes `fn(int)`).

## `map` / `filter` / `reduce` / `sum` / `range`

The functional core, all implemented as `for`-loop accumulation:

- `map(lst, f)` — `[f(x) for x in lst]`; `twice` on `[1..5]` →
  `[2,4,6,8,10]`.
- `filter(lst, pred)` — keeps matches; `is_even` → `[2,4]`.
- `reduce(lst, init, f)` — left fold `f(acc, x)`; `add2` from `0.0`
  → `15.0`.
- `sum(lst)` — literally `reduce(lst, 0.0, fn(a,b) a+b)` — note the
  upstream inline-lambda syntax; the tutorial uses a named `add2`
  (the `fn(p) expr` shorthand doesn't compile under the Python
  shim).
- `range(start, end)` — `[start..end)` exclusive-end list;
  `range(2,6)` → `[2,3,4,5]`, `range(0,0)` → `[]`.

## ⚠️ Runtime-shim notes (documented)

- `print`/`println` delegate to `io.print`/`io.println` — the
  `import stdlib.io` resolution issue applies, so the companion
  uses builtin `println` directly.
- `to_str` is `value as str` (a cast, not `str()`), `len` is
  `sizeof collection`, `assert` throws `AssertionError` — all
  compiler-target features; behavior under `ltlc run` is
  shim-dependent and noted rather than demoed.
- `sum`'s `fn(a, b) a + b` lambda syntax is module-file sugar; the
  tutorial passes named functions everywhere — the portable style.

## Verified results

```text
abs(-3.5)=3.5 abs(2.5)=2.5
clamp: 5→5.0, -1→0.0, 99→10.0
min(3,7)=3.0 max(3,7)=7.0
map twice=[2,4,6,8,10]  filter even=[2,4]
reduce add=15.0  sum=15.0  range(2,6)=[2,3,4,5]
```

`tests/test_core_tutorial.py` pins every value.

## When to use it

**Use it** (or rather, its patterns) everywhere — `clamp` for
saturated arithmetic, `map`/`filter`/`reduce` for data pipelines,
`range` for index loops. It's the vocabulary every other stdlib
module assumes.

**Don't expect** `Option`/`Result` wrappers, iterator laziness, or
partial application — `core` is deliberately minimal: functions,
lists, and folds.

That is `stdlib/core.ltl`: the twenty functions Lateralus programs
are built from.
