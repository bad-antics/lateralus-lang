---
title: "A Practical Tour of stdlib.set"
date: 2026-04-20
author: contributor
tags: [stdlib, tutorial, sets, pipelines]
---

# A Practical Tour of `stdlib.set`

Lateralus sets are **sorted, deduplicated lists**. There is no hidden hash
ordering, so every operation below produces the same output on every run,
platform, and backend (C99, LLVM, JS, WASM). This makes sets easy to test and
easy to reason about inside pipelines.

## Core invariant

A value `s` is a valid set if and only if:

1. it is a list,
2. its elements are in ascending order, and
3. it contains no duplicates.

Every function in `stdlib.set` accepts valid sets and returns valid sets.

## 1. Constructing a set

```lateralus
use stdlib.set

let s = [3, 1, 2, 3, 1] |> set.from_list
-- => [1, 2, 3]
```

`from_list` sorts and removes duplicates, so you can feed it arbitrary input.

## 2. Membership

```lateralus
[1, 2, 3] |> set.contains(2)   -- => true
[1, 2, 3] |> set.contains(9)   -- => false
```

## 3. Union

```lateralus
let a = [1, 2, 3]
let b = [3, 4, 5]

a |> set.union(b)
-- => [1, 2, 3, 4, 5]
```

## 4. Intersection

```lateralus
a |> set.intersection(b)
-- => [3]
```

## 5. Difference

Elements in `a` that are not in `b`:

```lateralus
a |> set.difference(b)
-- => [1, 2]
```

## 6. Symmetric difference

Elements in exactly one of the two sets:

```lateralus
a |> set.symmetric_difference(b)
-- => [1, 2, 4, 5]
```

## 7. Subset checks

```lateralus
[1, 2] |> set.is_subset([1, 2, 3])   -- => true
[1, 4] |> set.is_subset([1, 2, 3])   -- => false
```

## 8. Composing in pipelines

Because every operation returns a set, calls chain naturally:

```lateralus
[5, 3, 3, 1]
    |> set.from_list              -- [1, 3, 5]
    |> set.union([2, 3, 4])       -- [1, 2, 3, 4, 5]
    |> set.difference([1, 5])     -- [2, 3, 4]
```

## Edge cases

| Expression                          | Result      |
|-------------------------------------|-------------|
| `[] \|> set.union([1])`              | `[1]`       |
| `[1] \|> set.intersection([])`       | `[]`        |
| `[] \|> set.difference([1])`         | `[]`        |
| `[1, 1, 1] \|> set.from_list`        | `[1]`       |

## Pinned test vectors

These vectors are enforced by `tests/test_stdlib_set_vectors.py` and exercised
by `examples/set_basics.lt`, so this tutorial cannot silently drift from the
implementation.

| Operation                      | Input A       | Input B     | Expected         |
|--------------------------------|---------------|-------------|------------------|
| `from_list`                    | `[3,1,2,3,1]` | -           | `[1,2,3]`        |
| `union`                        | `[1,2,3]`     | `[3,4,5]`   | `[1,2,3,4,5]`    |
| `intersection`                 | `[1,2,3]`     | `[3,4,5]`   | `[3]`            |
| `difference`                   | `[1,2,3]`     | `[3,4,5]`   | `[1,2]`          |
| `symmetric_difference`         | `[1,2,3]`     | `[3,4,5]`   | `[1,2,4,5]`      |
| `is_subset`                    | `[1,2]`       | `[1,2,3]`   | `true`           |

## Takeaways

- Sets are plain sorted lists, so they print, serialize, and diff cleanly.
- All operations are deterministic and backend-independent.
- Chain operations with `|>` to build up set expressions without temporaries.