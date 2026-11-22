# Mastering Ring Buffers in Lateralus: Zero-Allocation Circular Queues, Sliding Windows, and Streaming

Dynamic collections (such as dynamic vectors and linked queues) continuously allocate, reallocate, and trigger garbage collection churn or memory fragmentation. In mission-critical software—such as audio DSP processing, network packet ingress (e.g., DPDK/eBPF ring buffers), high-frequency financial messaging, and Linux kernel dmesg logs—dynamic allocation on hot paths is unacceptable.

A **Circular Ring Buffer** provides a fixed-capacity FIFO data structure that operates entirely within preallocated bounds, offering $O(1)$ enqueue and $O(1)$ dequeue complexity with zero heap reallocations.

In this tutorial, we demonstrate how to design, simulate, and verify a robust circular ring buffer in Lateralus.

---

## 1. Architectural Principles: Head, Tail, and Modular Indexing

A ring buffer manages continuous streaming using two pointers and modular arithmetic:
- **`head`**: Read pointer indicating the oldest element in the queue.
- **`tail`**: Write pointer indicating where the next item will be placed.
- **`count`**: Current active element count ($0 \le \text{count} \le \text{capacity}$).

When an index reaches the buffer capacity, it wraps around back to zero via the modulo operator:

$$\text{next\_idx} = (\text{idx} + 1) \pmod{\text{capacity}}$$

```lateralus
fn rb_next_idx(current: int, cap: int) -> int {
    return (current + 1) % cap;
}
```

---

## 2. Invariants and State Predicates

A correctly constructed ring buffer satisfies three invariant conditions:
1. **Empty State**: $\text{count} == 0$. Dequeue operations return an empty sentinel or underflow error.
2. **Full State**: $\text{count} == \text{capacity}$. Enqueue operations either reject (backpressure) or overwrite the oldest element.
3. **Available Capacity**: $\text{available} = \text{capacity} - \text{count}$.

```lateralus
fn rb_is_empty(count: int) -> bool {
    return count == 0;
}

fn rb_is_full(count: int, cap: int) -> bool {
    return count >= cap;
}

fn rb_available_capacity(count: int, cap: int) -> int {
    return cap - count;
}
```

---

## 3. Streaming Lifecycles and Overwrite Semantics

When ingesting real-time sensor telemetry or audio samples, producers frequently favor newer data over stale metrics. In overwrite mode:
- If $\text{count} < \text{capacity}$, simply advance `tail` and increment `count`.
- If $\text{count} == \text{capacity}$, advance both `tail` and `head`, keeping `count == capacity` (overwriting the stale head element without allocating new memory).

---

## 4. End-to-End Verification

Our verification test suite demonstrates:
- Sequence of enqueues, capacity saturation, and modular wraparound back to index 0.
- Interleaved dequeues resetting head pointers.
- Re-enqueuing into freed circular slots.

See the complete runnable implementation:
- **Executable Example**: `examples/ringbuf_tutorial.ltl`
- **Unit Test Vectors**: `tests/stdlib_ringbuf_tutorial.ltl`

Run the compiler checks and test suites:
```bash
python -m lateralus_lang check examples/ringbuf_tutorial.ltl
python -m lateralus_lang check tests/stdlib_ringbuf_tutorial.ltl
pytest tests/test_compiler.py
```
