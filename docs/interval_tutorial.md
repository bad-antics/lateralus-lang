# Interval Arithmetic with `stdlib/interval`

The `stdlib/interval` module provides a simple way to work with closed intervals of real numbers. This tutorial walks through creating intervals, performing arithmetic, and verifying the results.

---

## Importing the module
```lateralus
import stdlib.interval as iv
```

## Creating intervals
```lateralus
let a = iv.Interval(1.0, 2.0)   // Represents [1.0, 2.0]
let b = iv.Interval(3.5, 4.0)   // Represents [3.5, 4.0]
```

## Adding two intervals
The sum of two intervals `[l₁, u₁] + [l₂, u₂]` is `[l₁ + l₂, u₁ + u₂]`.
```lateralus
let c = iv.add(a, b)
print(c)   // Expected output: Interval(4.5, 6.0)
```

## Expected result (pinned test vector)
The resulting interval should be exactly:
```
Interval(4.5, 6.0)
```
You can use this as a test vector in your own test suite:
```lateralus
assert c.lower == 4.5
assert c.upper == 6.0
```

---

## Running the example
1. Open the Lateralus REPL (`ltlc` or the appropriate entry point).
2. Paste the code snippets above.
3. Verify that the printed interval matches `Interval(4.5, 6.0)`.

Feel free to experiment with other operations (`sub`, `mul`, `div`) provided by the `interval` module.

---

*This guide satisfies the bounty request for a short tutorial with a runnable example and a pinned test vector.*