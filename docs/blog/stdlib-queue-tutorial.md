# Double-Ended Queues with `stdlib/queue.ltl`

A deque supports O(1) push/pop at both ends — the workhorse behind job
schedulers, BFS frontier queues, and undo buffers. `stdlib/queue.ltl`
implements one in about 120 lines over a plain list.

This tutorial exercises every operation. Companion:
`examples/queue_tutorial.ltl`.

---

## API

- **Construction:** `new()`, `from_list(items)`
- **Ends:** `push_back`, `push_front`, `pop_front`, `pop_back` — pops
  return `[value, new_queue]` since Lateralus values are immutable
- **Peeks:** `front`, `back` (return `nil` when empty)
- **Bulk:** `reversed`, `filter_queue`, `map_queue`, `drain(q, n)`,
  `concat`, `to_string`, plus `size`/`is_empty`

## One real bug the tutorial works around

`reversed(q)` called the `reverse` builtin — but the generated Python
`reverse` shim itself calls `reversed()`, which the module's own
`reversed` function shadows → **infinite recursion** (`RecursionError`).
The inlined copy reimplements reversal with an explicit index loop.
Module bug flagged for a fix PR.

## Running the tutorial

```bash
python -m lateralus_lang run examples/queue_tutorial.ltl
python -m lateralus_lang check examples/queue_tutorial.ltl
python -m pytest tests/test_queue_tutorial.py -x -q
```
