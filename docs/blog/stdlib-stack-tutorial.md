# LIFO Stack with `stdlib/stack.ltl`

`stdlib/stack.ltl` is the simplest data-structure module in the
stdlib: a LIFO stack represented as a plain list, where the **last
element is the top**. Push is append, pop is slice-off-the-end,
peek is index `len-1` — that's the whole implementation. On top of
that it adds the ergonomic extras every stack API needs:
`contains`, `reversed`, `swap_top`, `dup`, `drop`, `fold`, and
`to_string`.

Companion: `examples/stack_tutorial.ltl`.

---

## Representation

```text
stack = [bottom, …, top]        top = s[len(s)-1]
```

Because it's just a list, `size`/`is_empty` are `len` checks and
`new`/`clear` return `[]`. `from_list` copies element-by-element so
the last input element becomes the top.

## API walkthrough

| Function | Returns | Notes |
|---|---|---|
| `new()` / `from_list(items)` | stack | last element = top |
| `push(s, item)` | new stack | `s + [item]` |
| `pop(s)` | `[value, new_stack]` | `["", s]`-style sentinel when empty (upstream uses `nil`) |
| `peek(s)` | top or `nil` | no removal |
| `size` / `is_empty` / `contains` | int/bool | linear contains |
| `reversed(s)` | stack | bottom↔top swap via `reverse` |
| `swap_top(s)` | stack | exchanges top two; no-op if <2 |
| `dup(s)` | stack | duplicates top; no-op if empty |
| `drop(s, n)` | stack | removes top n, clamps at 0 (`max(0, len-n)`) |
| `map_stack` / `fold` | — | higher-order helpers over elements bottom→top |
| `to_string(s)` | `"Stack(...)"` | debug formatting |

## Verified results

```text
push a,b,c        -> [a,b,c] top=c
pop               -> c, rest [a,b]; peek=b
from_list [10,20,30] -> top=30 ; contains 20=T, 99=F
reversed          -> top becomes 10
swap_top [1,2,3]  -> [1,3,2]
dup [1,2]         -> [1,2,2]
drop 2 [1,2,3,4]  -> [1,2] ; drop 9 [1,2] -> []
fold([1,2,3,4],+) -> 10 ; fold([5,6], init=100) -> 111
```

`tests/test_stack_tutorial.py` pins every value.

## Design notes worth stealing

- **Pairs as returns**: `pop`/`swap_top`-style functions return
  `[value, new_stack]` rather than mutating — persistent data
  structure style, no aliasing surprises.
- **Saturating `drop`**: `max(0, len(s)-n)` means dropping more than
  the size silently yields empty instead of erroring — convenient
  but lossy; check `size` first if that matters.
- **`fold` order**: iterates bottom→top (`for el in s`), so
  `fold([1,2,3,4], +)` = 10 — opposite of a "reduce top-first"
  intuition; the doc comment calls this out explicitly.

## When to use it

**Use it** for DFS worklists, undo buffers, expression parsing
(shunting-yard), bracket matching, and anywhere "process the most
recent thing first" is the rule.

**Don't expect** thread safety, capacity limits, or typed elements —
it's a list with conventions. For the priority-ordered cousin see
the heap tutorial; for FIFO see queue/deque.

That is `stdlib/stack.ltl`: LIFO in forty lines, plus the helpers
that make it pleasant.
