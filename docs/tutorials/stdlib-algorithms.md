# Practical Sorting, Searching, and Math with `stdlib.algorithms`

The Lateralus standard library ships `stdlib/algorithms.ltl`, offering idiomatic implementations of classical data structure manipulations, divide-and-conquer sorting, logarithmic-time searching, and foundational number theory.

---

## Core Algorithm Helpers

### Sorting and Searching
- `merge_sort(arr: list) -> list`: Stable $O(n \log n)$ divide-and-conquer sorting.
- `binary_search(arr: list, target) -> int`: Logarithmic $O(\log n)$ search on presorted collections. Returns 0-based index or `-1` if absent.
- `linear_search(arr: list, target) -> int`: $O(n)$ search for unsorted lists.

### Sequence & List Transformations
- `unique(arr: list) -> list`: Preserves first occurrences and strips duplicates.
- `chunk(arr: list, size: int) -> list`: Partitions an array into uniform sub-slices of maximum length `size`.
- `sliding_window(arr: list, size: int) -> list`: Produces overlapping sliding frames of length `size`.
- `flatten(arr: list) -> list`: Recursively flattens arbitrarily nested lists.

### Number Theory
- `primes_up_to(n: int) -> list`: Sieve generating all prime numbers $\le n$.
- `is_prime(n: int) -> bool`: Primality testing with trial division.
- `gcd(a, b)` / `lcm(a, b)`: Greatest common divisor and least common multiple via Euclidean algorithm.
- `fibonacci_sequence(n: int) -> list`: Generates the first `n` terms of the Fibonacci sequence.

---

## Runnable Example

```lateralus
import algorithms

fn main() {
    let raw = [64, 34, 25, 12, 22, 11, 90]
    let sorted_items = merge_sort(raw)
    println("Sorted: " + str(sorted_items))

    let idx = binary_search(sorted_items, 25)
    println("Index of 25: " + str(idx))

    let primes = primes_up_to(30)
    println("Primes: " + str(primes))
}

main()
```
