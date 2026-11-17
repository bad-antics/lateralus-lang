# Interval Arithmetic Tutorial

The `stdlib/interval` module provides a simple way to work with numeric intervals and perform interval arithmetic. This guide walks through creating intervals, adding them, and checking the resulting bounds.

## Importing the Module
```lateralus
import stdlib/interval
```

## Creating Intervals
Use the `interval(lower, upper)` constructor to create an interval:
```lateralus
let a = interval(1.0, 2.0)   // Represents [1.0, 2.0]
let b = interval(3.5, 4.0)   // Represents [3.5, 4.0]
```

## Adding Intervals
Interval addition is performed with the `+` operator. The resulting interval's lower bound is the sum of the lower bounds, and the upper bound is the sum of the upper bounds.
```lateralus
let c = a + b   // c is [4.5, 6.0]
print("Resulting interval:", c)   // Expected output: interval(4.5, 6.0)
```

## Expected Result
The addition of `a` and `b` yields:
- **Lower bound:** `1.0 + 3.5 = 4.5`
- **Upper bound:** `2.0 + 4.0 = 6.0`

Thus `c` is the interval `[4.5, 6.0]`.

## Running the Example
Save the above code in a file (e.g., `example.ls`) and execute it with the Lateralus interpreter:
```sh
lateralus run example.ls
```
You should see:
```
Resulting interval: interval(4.5, 6.0)
```

## Test Vector
The following test confirms the bounds of the resulting interval:
```lateralus
import stdlib/interval
import stdlib/assert

let a = interval(1.0, 2.0)
let b = interval(3.5, 4.0)
let c = a + b

assert.equal(c.lower, 4.5)
assert.equal(c.upper, 6.0)
```
Add this test to your test suite to ensure future changes do not break interval addition.
