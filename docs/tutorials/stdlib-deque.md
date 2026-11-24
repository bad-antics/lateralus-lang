# Versatile Bidirectional Queuing with `stdlib.deque`

The `stdlib.deque` module provides a double-ended queue (deque) supporting efficient element insertion, extraction, peeking, and cyclic rotation from both ends. It powers task schedulers, work-stealing thread pools, sliding-window buffers, browser navigation history (undo/redo), and breadth-first search (BFS) algorithms.

---

## 1. Deque Initialization

Construct an empty deque, convert from an existing list, or initialize repeated values:

```lateralus
import deque

// Create an empty deque
let q = deque.new()

// Initialize from existing items
let workers = deque.from_list(["worker-1", "worker-2", "worker-3"])

// Initialize with repeated default values
let zeros = deque.repeat(0, 5) // [0, 0, 0, 0, 0]
```

---

## 2. Bidirectional Push, Pop, and Peek

Deques allow interacting symmetrically at both the head (front) and tail (back):

| Operation | Front Method | Back Method | Description |
| :--- | :--- | :--- | :--- |
| **Push** | `push_front(d, item)` | `push_back(d, item)` | Appends item to specified end. |
| **Peek** | `front(d)` | `back(d)` | Returns boundary value without modifying deque (`nil` if empty). |
| **Pop** | `pop_front(d)` | `pop_back(d)` | Returns `[value, new_deque]`. |

```lateralus
let d = deque.new()
d = deque.push_back(d, "Middle")
d = deque.push_front(d, "High Priority")
d = deque.push_back(d, "Low Priority")
// Contents: ["High Priority", "Middle", "Low Priority"]

let f = deque.front(d) // "High Priority"
let b = deque.back(d)  // "Low Priority"

// Pop highest priority item
let res = deque.pop_front(d)
let task = res[0]      // "High Priority"
let updated_d = res[1] // ["Middle", "Low Priority"]
```

---

## 3. Cyclic Rotation

Rotate elements in circular order without allocating temporary intermediate arrays:

- **`rotate_left(d, n)`**: Shifts elements left by `n` positions (front elements wrap around to the back).
- **`rotate_right(d, n)`**: Shifts elements right by `n` positions (back elements wrap around to the front).

```lateralus
let items = deque.from_list([1, 2, 3, 4, 5])

// Round-robin shift (step 1)
let next_turn = deque.rotate_left(items, 1)
// next_turn == [2, 3, 4, 5, 1]

// Clockwise shift
let prev_turn = deque.rotate_right(items, 2)
// prev_turn == [4, 5, 1, 2, 3]
```

---

## 4. Query & Transformation Primitives

- **`size(d)` / `is_empty(d)`**: Inspect capacity and occupancy.
- **`contains(d, val)`**: Returns `true` if target element exists.
- **`at(d, idx)`**: Returns element at index `0` (front) to `size - 1` (back).
- **`reverse(d)`**: Inverts element order.
- **`extend(d, list)` / `extend_front(d, list)`**: Concatenates lists to either end.
- **`remove_all(d, val)`**: Filters out matching occurrences.

```lateralus
let q = deque.from_list([10, 20, 30])
let exists = deque.contains(q, 20) // true
let first = deque.at(q, 0)         // 10
let reversed_q = deque.reverse(q)  // [30, 20, 10]
```

---

## 5. End-to-End Example: Work-Stealing Task Dispatcher

```lateralus
import deque

fn main() {
    let job_queue = deque.new()
    
    // Normal jobs queue up in FIFO order at the back
    job_queue = deque.push_back(job_queue, "Render Report")
    job_queue = deque.push_back(job_queue, "Sync Database")
    
    // Emergency job preempts the queue at the front
    job_queue = deque.push_front(job_queue, "HOTFIX: Restart Service")
    
    while !deque.is_empty(job_queue) {
        let step = deque.pop_front(job_queue)
        let job = step[0]
        job_queue = step[1]
        println("Worker executing: " + job)
    }
}
```
