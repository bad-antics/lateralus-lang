# Keep the latest telemetry readings with Lateralus ringbuf

A sensor keeps sending readings, but your display needs only the latest three.
A ring buffer gives that history a fixed capacity: when it fills, the next push
replaces the oldest reading. Lateralus provides this behavior in
[`stdlib/ringbuf.ltl`](../../stdlib/ringbuf.ltl).

This tutorial uses the repository's actual module, with no implementation copied
into the example. It was checked against Lateralus 3.2.0 at
[`cdcec06253ad0079fd694775f333bbb3da90623f`](https://github.com/bad-antics/lateralus-lang/tree/cdcec06253ad0079fd694775f333bbb3da90623f).
The tested target is the Python backend; this article makes no claim about the C,
WASM, or bytecode targets.

## Run the example

From a checkout containing these tutorial files, with Python 3.10 or later:

```sh
python3 examples/tutorials/run_ringbuf_tutorial.py
```

No third-party Python packages are needed. The runner reads the unchanged
`stdlib/ringbuf.ltl`, appends the example source, compiles the combined source
through `Compiler` with `Target.PYTHON`, and executes the generated Python.
It also checks the output and boundary cases. Combining the sources explicitly
avoids relying on stdlib import resolution; the calls below refer directly to the
module's functions. Do not run the example file alone and expect those functions
to have been imported automatically.

The complete [example](../../examples/tutorials/ringbuf_tutorial.ltl) is:

```lateralus
// Keep the latest three telemetry readings using stdlib/ringbuf.ltl.
// Run with: python3 examples/tutorials/run_ringbuf_tutorial.py
// The runner compiles this file together with the unchanged stdlib module.
let readings = new(3)
for reading in [18, 21, 19, 23] {
    readings = push(readings, reading)
}
println(to_list(readings))
println(peek_front(readings))
println(peek_back(readings))
let removed = pop(readings)
println(removed[0])
readings = removed[1]
println(to_list(readings))
readings = push(readings, 24)
println(to_list(readings))
readings = clear(readings)
println(count(readings))
println(capacity(readings))
```

Expected output, pinned in the runner:

```text
[21, 19, 23]
21
23
21
[19, 23]
[19, 23, 24]
0
3
Verified 18 pinned checks against stdlib/ringbuf.ltl (Python backend).
```

## Follow the buffer through a wrap-around

`new(3)` creates an empty buffer with room for three values. The first three
pushes fill it with `[18, 21, 19]`. Pushing `23` replaces `18`, so `to_list`
returns `[21, 19, 23]` in chronological order even though the backing storage has
wrapped around. Use `to_list`, `peek_front`, and `peek_back` instead of reading the
internal list slots directly.

Keep assigning the value returned by `push`: `readings = push(readings, reading)`.
This implementation constructs and returns a new buffer. Calling `push` and
ignoring its result leaves the original buffer unchanged. That behavior is
verified by retaining the initial empty buffer in the runner.

`pop` returns a pair represented as a list: `[oldest_value, remaining_buffer]`.
The example prints `21`, then assigns `removed[1]` back to `readings`. Pushing
`24` afterwards gives `[19, 23, 24]`. This is useful when a consumer reads one
pending sample while the producer keeps supplying newer ones.

Finally, `clear` returns an empty buffer with the same capacity. Assign its
result too: the final count is `0`, and the capacity remains `3`.

## Pinned vectors and edge cases

The [verification script](../../examples/tutorials/run_ringbuf_tutorial.py)
performs 18 checks, including the complete example's exact stdout. These are
fixed expected results, not values computed from another call to the same
implementation:

| Operation | Expected result |
| --- | --- |
| Capacity 3, push 18, 21, 19, 23 | `[21, 19, 23]` |
| Pop that buffer | Value `21`, remaining `[19, 23]` |
| Push 24 into the remaining buffer | `[19, 23, 24]` |
| Clear it | Empty contents, capacity `3` |
| Capacity 1, push 7, then 9 | `[9]` |
| Pop an empty buffer | `nil` value, unchanged empty buffer |
| Read index 1 from the one-element buffer | `nil` |

The runner prints Python's representation of lists. Lateralus `nil` becomes
Python `None` in the verification code. Because `nil` is also a storable value,
use `is_empty` or `count` if you need to distinguish an empty pop from a stored
`nil`.

## Know the current limits

Use a positive capacity. `new` does not validate it, and pushing into a
zero-capacity buffer reaches a modulo-by-zero operation. This tutorial uses only
positive capacities.

The current `drain` function returns the contents but does **not** clear the
buffer, despite its source comment. The runner pins that observed behavior. To
consume everything, get `to_list(readings)` and then assign
`readings = clear(readings)` explicitly.

Fixed capacity describes the number of retained items, not allocation-free or
constant-time execution. The current `push` rebuilds the backing list with a
loop and concatenation. This article does not claim a throughput improvement or
a particular time bound for that implementation. It is also not a concurrent
queue: coordinate readers and writers outside this module.

The pattern is useful for bounded telemetry histories, recent event displays,
or a small rolling context. If every item must be delivered, overwriting the
oldest value is the wrong policy; use a queue with explicit backpressure instead.
