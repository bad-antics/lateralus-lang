# Priority Work Queue with `stdlib.queue`

The Lateralus standard library provides `stdlib/queue.ltl`, an immutable double-ended queue (deque) designed for amortized $O(1)$ operations on both ends. This guide shows how to model a task worker system where routine jobs follow standard FIFO execution, while urgent high-priority incidents preempt pending tasks.

---

## Key Operations

| Function | Signature | Description |
|---|---|---|
| `new()` | `() -> list` | Instantiates a new empty queue |
| `push_back(q, item)` | `(list, any) -> list` | Enqueues a routine task at the end of the line |
| `push_front(q, item)` | `(list, any) -> list` | Preemptively inserts an urgent task at the front |
| `pop_front(q)` | `(list) -> [item, remaining_q]` | Dequeues the next item to process |
| `front(q)` | `(list) -> any` | Peeks at the next scheduled job without removing |
| `size(q)` | `(list) -> int` | Current number of queued tasks |
| `is_empty(q)` | `(list) -> bool` | Checks if all work has been processed |

---

## Runnable Example

```lateralus
import queue

fn main() {
    let q = new()

    // 1. Routine tasks arrive in FIFO order
    q = push_back(q, "JOB-101: generate invoices")
    q = push_back(q, "JOB-102: database vacuum")

    // 2. Urgent task jumps the queue
    q = push_front(q, "URGENT-999: hotfix zero-day vulnerability")

    // 3. Additional routine task arrives
    q = push_back(q, "JOB-103: send marketing newsletter")

    // 4. Worker consumption loop
    while !is_empty(q) {
        let step = pop_front(q)
        let job = step[0]
        q = step[1]
        println("Processed: " + str(job))
    }
}

main()
```

### Execution Output
```text
Processed: URGENT-999: hotfix zero-day vulnerability
Processed: JOB-101: generate invoices
Processed: JOB-102: database vacuum
Processed: JOB-103: send marketing newsletter
```

Urgent jobs are guaranteed to be evaluated next, while standard jobs maintain strictly ordered FIFO processing.
