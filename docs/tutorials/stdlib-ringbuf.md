# High-Throughput Circular Buffering with `stdlib.ringbuf`

The `stdlib.ringbuf` module provides a fixed-size circular buffer (ring buffer) with wrap-around semantics. It provides an efficient $O(1)$ memory structure for bounded event streaming, moving-average computation, sliding windows, audio frames, and in-memory log history without unbounded dynamic heap reallocations.

---

## 1. Buffer Initialization & State

Create a fixed-capacity ring buffer or initialize directly from a sequence:

```lateralus
import ringbuf

// Create an empty ring buffer of capacity 5
let buf = ringbuf.new(5)

let cap = ringbuf.capacity(buf)   // 5
let empty = ringbuf.is_empty(buf) // true
let full = ringbuf.is_full(buf)   // false
let cnt = ringbuf.count(buf)      // 0
```

---

## 2. Ingestion & Overwrite Semantics

When `push()` is called on a buffer that has reached capacity, it automatically overwrites the oldest element and advances the head pointer:

```lateralus
let b = ringbuf.new(3)
b = ringbuf.push(b, "Alpha")
b = ringbuf.push(b, "Beta")
b = ringbuf.push(b, "Gamma")
// Buffer is full: ["Alpha", "Beta", "Gamma"]

// Pushing a 4th element overwrites "Alpha"
b = ringbuf.push(b, "Delta")
let items = ringbuf.to_list(b)
// items == ["Beta", "Gamma", "Delta"]
```

---

## 3. FIFO Extraction & Inspection

Inspect both endpoints of the circular queue or pop the oldest element:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`peek_front(buf)`** | `list -> any` | Returns the oldest element without modifying buffer state. Returns `nil` if empty. |
| **`peek_back(buf)`** | `list -> any` | Returns the newest element without modifying buffer state. Returns `nil` if empty. |
| **`pop(buf)`** | `list -> [val, new_buf]` | Removes and returns the oldest element and the updated buffer. |
| **`at(buf, index)`** | `(list, int) -> any` | Accesses element at logical index `0 .. count - 1` (`0` = oldest). |

```lateralus
let oldest = ringbuf.peek_front(b) // "Beta"
let newest = ringbuf.peek_back(b)  // "Delta"

let popped = ringbuf.pop(b)
let removed_val = popped[0]        // "Beta"
let remaining = popped[1]          // Buffer now holds ["Gamma", "Delta"]
```

---

## 4. Bulk Transformations & Drainage

- **`to_list(buf)`**: Exports all stored elements in FIFO order (oldest to newest).
- **`drain(buf)`**: Extracts all items, returning a list of contents.
- **`clear(buf)`**: Resets buffer state to empty while preserving configured capacity.
- **`map_buf(buf, fn)`**: Maps a transform function across all elements into a new ring buffer.

```lateralus
let history = ringbuf.from_list([10, 20, 30])
let double_fn = fn(x: int) -> int { return x * 2 }
let doubled_buf = ringbuf.map_buf(history, double_fn)
// to_list(doubled_buf) == [20, 40, 60]
```

---

## 5. End-to-End Example: Sliding Window Metric Smoother

```lateralus
import ringbuf

fn main() {
    let window_size = 4
    let metrics_history = ringbuf.new(window_size)
    let sensor_stream = [100.0, 102.5, 105.0, 110.0, 115.0, 120.0]

    for sample in sensor_stream {
        metrics_history = ringbuf.push(metrics_history, sample)
        
        let current_window = ringbuf.to_list(metrics_history)
        let sum = 0.0
        for v in current_window {
            sum = sum + v
        }
        let moving_avg = sum / float(len(current_window))
        println("Sample: " + to_str(sample) + " | Smoothed Avg: " + to_str(moving_avg))
    }
}
```
