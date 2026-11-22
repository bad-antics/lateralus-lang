# Result and Option Types with `stdlib/result.ltl`

`stdlib/result.ltl` implements the two workhorse types of
functional error handling — **Result** (`Ok`/`Err`) and **Option**
(`Some`/`None`) — as plain tagged maps, plus the combinators that let
you chain fallible computations without nested `if`s.

This tutorial walks constructors, predicates, `map`/`and_then`-style
transformers, Result↔Option interop, and the list helpers
`collect_results` and `partition_results`. Companion:
`examples/result_tutorial.ltl`.

---

## Tagged maps, not classes

A Result is a map with a `"_tag"` discriminator:

```ltl
ok(21)    // {"_tag": "Ok", "value": 21, "is_ok": true, ...}
err("div by zero")
```

Predicates `is_ok`/`is_err` (and `is_some`/`is_none` for Options)
read the tag; `unwrap`, `unwrap_or`, `unwrap_err`,
`unwrap_option`, `unwrap_option_or` extract payloads, throwing
`ValueError` on the wrong variant.

## Chaining without nesting

`map_result` transforms the success value, `map_err` the failure,
`and_then`/`or_else` flatten nested Results, and `flatten` collapses
`Ok(Ok(x))`. Options mirror this with `map_option`,
`option_and_then`, `option_or`. Interop is two functions:
`option_to_result(o, err)` and `result_to_option(r)`.

```ltl
ok(5) |> and_then(fn(x) { return ok(x + 1) })
      |> and_then(fn(x) { return ok(x * 10) })
// unwrap -> 60
```

## Collections

`collect_results` turns `[Ok, Ok, ...]` into `Ok([v, ...])` and
short-circuits on the first `Err`. `partition_results` splits a mixed
list into `{oks: [...], errs: [...]}`.

---

## Representation details that differ from the module draft

The tutorial inlines the module with four fixes needed to run it on
the current toolchain:

1. **Map literals don't parse** — `{"_tag": "Ok", ...}` is rejected;
   Results are built by imperative `m["key"] = value` writes.
2. **`"_tag" in v` membership isn't supported** — `is_result`/
   `is_option` use `contains(keys(v), "_tag")`.
3. **`type_of`/`typeof` don't yield comparable names** — the guard is
   dropped; tag checks alone discriminate.
4. **`try_call`/`try_call_with` can't run** — `try/catch` transpiles
   to invalid Python on the `run` backend, so they are documented but
   not demoed.
