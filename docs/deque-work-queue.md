# A small work queue with `stdlib/deque.ltl`

A deque lets a program add or remove work at either end. Imagine jobs numbered
20 and 30 waiting in order. A priority job 10 belongs at the front; ordinary job
40 goes to the back. After processing job 10 and withdrawing job 40, jobs 20
and 30 should still be waiting in that order.

This tutorial uses the actual `stdlib/deque.ltl` implementation. It was prepared
with AI assistance and checked against repository commit
`d078809df3f5db544b7efa7b0979c7a43ebb25e6`, using the parser and Python backend.
It is a new contribution, with no claim of prior client deployments.

## Build and consume the queue

```ltl
let jobs = from_list([20, 30])
jobs = push_front(jobs, 10)
jobs = push_back(jobs, 40)
// jobs is now [10, 20, 30, 40]

let first_job = pop_front(jobs)
// first_job is [10, [20, 30, 40]]
jobs = first_job[1]

let last_job = pop_back(jobs)
// last_job is [40, [20, 30]]
jobs = last_job[1]
```

Reassign the returned queue. `push_front`, `push_back` and the pop functions
return their result; calling them and discarding that result does not advance
your `jobs` variable. Each pop returns a two-element list: the removed value
at index 0 and the remaining queue at index 1.

This implementation represents a deque with a list. It builds new lists using
concatenation and slicing. Do not assume constant-time endpoint operations,
bounded memory or suitability for a high-volume production queue.

## Rotate without losing work

Rotation moves jobs from one end to the other. Counts wrap around the queue
length, so rotating a four-item queue five places has the same effect as one.

```ltl
rotate_left([10, 20, 30, 40], 5)   // [20, 30, 40, 10]
rotate_right([10, 20, 30, 40], 5)  // [40, 10, 20, 30]
rotate_right([10, 20, 30, 40], 0)  // [10, 20, 30, 40]
```

The example deliberately includes a zero rotation and a count larger than the
queue, rather than demonstrating only the happy path. An empty queue stays
empty under either rotation.

## Handle empty queues and invalid indexes

`at(jobs, index)` returns `nil` for a negative or out-of-range index.
`pop_front([])` and `pop_back([])` return `[nil, []]`. Check the result before
using it as a real job. If a queue may contain `nil` as a legitimate value,
check `is_empty` before popping so empty and present-nil cases remain distinct.

`clear(jobs)` returns an empty queue. As with insertion, assign it if the
caller wants to replace its current queue.

## Run the pinned example

From a checkout with Python 3.10 or later:

```text
python scripts/run_deque_tutorial.py
python -m pytest tests/test_deque_tutorial.py -q
```

The runner concatenates the **unmodified** deque module with
`examples/deque_work_queue.ltl`, parses the combined Lateralus source and
transpiles it through the repository's Python backend. It executes the generated
Python and compares all ten output lines with the committed expected file.
This is an explicit workaround for the Python backend's unresolved stdlib
import surface, not a claim that `import deque` works in a standalone example.
It does not replace deque functions with Python `collections.deque`.

Expected Python-backend output is pinned as:

```text
[10, 20, 30, 40]
10
40
[20, 30]
[20, 30, 40, 10]
[40, 10, 20, 30]
[10, 20, 30, 40]
None
[None, []]
True
```

`None` and `True` are the Python backend's printed spellings of Lateralus
`nil` and `true`. The five focused tests additionally check invalid indexes,
both empty pops, empty rotations, a rotation inverse, reassignment and clearing.
No native C, WASM, performance or deployment result is claimed.
