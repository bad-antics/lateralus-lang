# stdlib.stack Tutorial

The `stdlib/stack.ltl` module implements a classic **LIFO (Last‑In‑First‑Out)** stack data structure. This tutorial walks through the core operations:

- **push** – add an element to the top of the stack
- **pop** – remove and return the top element
- **peek** – look at the top element without removing it
- **isEmpty** – check whether the stack contains any elements

## 1. Creating a Stack
```lateralus
import stdlib.stack as Stack

// Create a new, empty stack
let s = Stack.new()
```

## 2. Pushing Values
```lateralus
Stack.push(s, 10)
Stack.push(s, 20)
```
After these calls the stack contains `[10, 20]` with `20` at the top.

## 3. Peeking at the Top
```lateralus
let top = Stack.peek(s)   // → 20
```
`peek` returns the current top element without modifying the stack.

## 4. Popping Values
```lateralus
let popped1 = Stack.pop(s)   // → 20
let popped2 = Stack.pop(s)   // → 10
```
Elements are removed in **reverse** order of insertion (LIFO).

## 5. Empty‑Stack Handling
```lateralus
let emptyNow = Stack.isEmpty(s)   // → true
```
Attempting to `pop` or `peek` an empty stack will raise a runtime error; therefore you should always check `isEmpty` first.

## 6. Full Runnable Example
Below is a self‑contained script you can paste into the Lateralus REPL or run as a file.
```lateralus
import stdlib.stack as Stack
import stdlib.print as Print

let s = Stack.new()
Print.println("Is empty? " + Stack.isEmpty(s))   // true

Stack.push(s, 1)
Stack.push(s, 2)
Print.println("Top after pushes: " + Stack.peek(s))   // 2

let p1 = Stack.pop(s)
Print.println("Popped: " + p1)                     // 2
Print.println("Top now: " + Stack.peek(s))        // 1

Stack.pop(s)   // removes the last element
Print.println("Is empty after all pops? " + Stack.isEmpty(s)) // true
```
**Expected output**
```
Is empty? true
Top after pushes: 2
Popped: 2
Top now: 1
Is empty after all pops? true
```

## 7. Test Vectors (Pinned)
The repository includes a deterministic test suite (`tests/stdlib/stack_tutorial_test.ltl`) that asserts the exact values shown above. Running the test guarantees the tutorial remains accurate.

---
*Feel free to experiment with other data types – the stack works with any value supported by Lateralus.*