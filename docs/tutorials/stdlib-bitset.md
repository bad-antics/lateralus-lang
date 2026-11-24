# High-Performance Set Operations with `stdlib.bitset`

The `stdlib.bitset` module provides a memory-efficient, fixed-capacity bitset for tracking and performing high-speed boolean and set operations on non-negative integers. It stores packed bits across 32-bit machine words and provides bitwise union, intersection, difference, and membership testing.

---

## 1. Constructing a Bitset

Create an empty bitset with a fixed maximum capacity or initialize one directly from a list of integer indices:

```lateralus
import bitset

// Create bitset capable of holding indices 0..63
let bs = bitset.new(64)

// Initialize bitset with pre-set active positions
let flags = bitset.from_list(64, [0, 5, 12, 31, 48])
```

The underlying bitset is dynamically partitioned across internal 32-bit words with bounds verification.

---

## 2. Core Bit Manipulation

Modify and query individual bit states:

```lateralus
// Set a bit at position 10
let bs = bitset.set(bs, 10)

// Test membership / bit state (returns bool)
let is_active = bitset.test(bs, 10) // true
let not_set = bitset.test(bs, 42)   // false

// Toggle bit state
let bs = bitset.toggle(bs, 10) // clears bit 10
let bs = bitset.toggle(bs, 10) // sets bit 10 again

// Explicitly clear a bit
let bs = bitset.clear(bs, 10)
```

---

## 3. Bitset Algebra and Set Operations

Combine and compare bitsets with set operations:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`union(a, b)`** | `(list, list) -> list` | Bitwise OR ($A \cup B$): all bits present in either $a$ or $b$. |
| **`intersection(a, b)`** | `(list, list) -> list` | Bitwise AND ($A \cap B$): bits present in both $a$ and $b$. |
| **`difference(a, b)`** | `(list, list) -> list` | Bitwise relative complement ($A \setminus B$): bits in $a$ but not $b$. |
| **`symmetric_difference(a, b)`**| `(list, list) -> list` | Bitwise XOR ($A \Delta B$): bits in either $a$ or $b$, but not both. |
| **`is_subset(a, b)`** | `(list, list) -> bool` | Checks if every set bit in $a$ is also present in $b$. |

### Example Operations:

```lateralus
let set_a = bitset.from_list(64, [1, 2, 3, 4])
let set_b = bitset.from_list(64, [3, 4, 5, 6])

let all_elements = bitset.union(set_a, set_b)          // [1, 2, 3, 4, 5, 6]
let shared_elements = bitset.intersection(set_a, set_b) // [3, 4]
let only_in_a = bitset.difference(set_a, set_b)        // [1, 2]
let either_not_both = bitset.symmetric_difference(set_a, set_b) // [1, 2, 5, 6]

let is_sub = bitset.is_subset(shared_elements, set_a)  // true
```

---

## 4. Inspection and Serialization

Query bit counts, extract indices, or convert to string formats:

```lateralus
let active_count = bitset.count(all_elements)    // 6
let is_empty = bitset.is_empty(all_elements)      // false
let indices = bitset.to_list(all_elements)        // [1, 2, 3, 4, 5, 6]

// Formatted string representation
let str_repr = bitset.to_string(all_elements)    // "Bitset([1, 2, 3, 4, 5, 6])"
```
