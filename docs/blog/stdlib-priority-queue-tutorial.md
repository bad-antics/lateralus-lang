# Mastering Binary Min-Heaps in Lateralus: O(log N) Priority Queues, Sift-Down Invariants, and Task Scheduling

Standard FIFO queues dispatch items purely based on arrival order. In operational systems—such as operating system process schedulers, asynchronous event loop timer wheels (e.g., `epoll` / `libuv`), packet traffic shapers, and graph search algorithms (Dijkstra and A*)—tasks must be processed strictly in order of **urgency or deadline priority**, not arrival sequence.

A **Binary Min-Heap** implements an optimal Priority Queue where:
- Checking the minimum element takes $O(1)$ time.
- Inserting an element takes $O(\log N)$ time.
- Extracting the minimum element takes $O(\log N)$ time.

In this tutorial, we demonstrate how to construct, manipulate, and verify an array-backed binary min-heap priority queue in Lateralus.

---

## 1. Mathematical Anatomy: The Flat Array Tree

Rather than using dynamically allocated pointer nodes, a complete binary tree can be packed contiguously into a flat array:

```
               [5] (idx 0)
              /   \
            /       \
      (idx 1) [10]  [20] (idx 2)
              /  \
     (idx 3) [50] [70] (idx 4)
```

For any zero-indexed element at index $i$:
- **Parent Index**: $\lfloor (i - 1) / 2 \rfloor$
- **Left Child Index**: $2i + 1$
- **Right Child Index**: $2i + 2$

**Min-Heap Invariant**: Every parent node must be less than or equal to its children:
$$\text{heap}[\text{parent}(i)] \le \text{heap}[i]$$

---

## 2. Invariant Restoration: Sift-Up and Sift-Down

### Sift-Up (Bubble-Up)
When appending a new element to the end of the array, it bubbles upward until the heap invariant is restored:

```lateralus
fn pq_sift_up(heap: list, start_idx: int) -> int {
    let mut idx = start_idx;
    while idx > 0 {
        let parent = (idx - 1) / 2;
        if heap[idx] < heap[parent] {
            let tmp = heap[idx];
            heap[idx] = heap[parent];
            heap[parent] = tmp;
            idx = parent;
        } else {
            break;
        }
    }
    return 0;
}
```

### Sift-Down (Sink)
When extracting the root minimum, the last element fills the root slot and sinks downward by swapping with the smaller of its two children:

```lateralus
fn pq_sift_down(heap: list, start_idx: int) -> int {
    let mut idx = start_idx;
    let n = len(heap);
    while 2 * idx + 1 < n {
        let left = 2 * idx + 1;
        let right = 2 * idx + 2;
        let mut smallest = idx;
        if heap[left] < heap[smallest] { smallest = left; }
        if right < n && heap[right] < heap[smallest] { smallest = right; }
        if smallest != idx {
            let tmp = heap[idx];
            heap[idx] = heap[smallest];
            heap[smallest] = tmp;
            idx = smallest;
        } else {
            break;
        }
    }
    return 0;
}
```

---

## 3. Real-World Task Scheduling Scenario

In timer management, deferred tasks carry future execution deadlines. When the event loop ticks, the top of the heap is inspected in $O(1)$. If the earliest deadline has not expired, no tasks run; if expired, tasks are popped in chronological sequence.

See `examples/priority_queue_tutorial.ltl` for a runnable demonstration scheduling jobs with varying millisecond offsets.

---

## 4. End-to-End Verification with Golden Vectors

Our verification suite confirms:
- Inserting an arbitrary unordered permutation (`[50, 10, 80, 20, 5, 70]`).
- Sequential root extractions yielding a strictly sorted ascending sequence (`[5, 10, 20, 50, 70, 80]`).
- Clean heap exhaustion and single-element bounds.

Run compiler verification and test suites:
```bash
python -m lateralus_lang check examples/priority_queue_tutorial.ltl
python -m lateralus_lang check tests/stdlib_priority_queue_tutorial.ltl
pytest tests/test_compiler.py
```
