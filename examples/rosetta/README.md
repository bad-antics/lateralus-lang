# Rosetta Code — Lateralus Implementations

Canonical programming tasks implemented in Lateralus. Each file is a
self-contained `.ltl` you can run with `lateralus run <file>`.

These are deliberate ports of tasks that appear on
[rosettacode.org](https://rosettacode.org) — useful both as a comparative
reference and as discoverability ("Rosetta Code in X" searches).

## Tasks

| Task                        | File                                        | Showcases                        |
|-----------------------------|---------------------------------------------|----------------------------------|
| FizzBuzz                    | [`fizzbuzz.ltl`](fizzbuzz.ltl)              | control flow                     |
| Luhn Checksum               | [`luhn.ltl`](luhn.ltl)                      | digit arithmetic, integer mod    |
| Levenshtein Distance        | [`levenshtein.ltl`](levenshtein.ltl)        | 2-D dp, string distance          |
| Roman Numerals (to/from)    | [`roman.ltl`](roman.ltl)                    | table-driven conversion          |
| Sieve of Eratosthenes       | [`sieve.ltl`](sieve.ltl)                    | list mutation, number theory     |
| Caesar Cipher               | [`caesar.ltl`](caesar.ltl)                  | char arithmetic                  |
| 0/1 Knapsack                | [`knapsack.ltl`](knapsack.ltl)              | dynamic programming              |
| N-Queens                    | [`nqueens.ltl`](nqueens.ltl)                | recursion + backtracking         |
| Topological Sort            | [`topological_sort.ltl`](topological_sort.ltl) | graphs, Kahn's algorithm     |
| Huffman Coding              | [`huffman.ltl`](huffman.ltl)                | trees + greedy                   |
| JSON Mini Parser            | [`json_mini.ltl`](json_mini.ltl)            | recursive-descent parsing        |
| 100 Doors                   | [`doors.ltl`](doors.ltl)                    | loops, array indexing            |
| Binary Search               | [`binary_search.ltl`](binary_search.ltl)      | algorithms, slicing              |
| Bubble Sort                 | [`bubble_sort.ltl`](bubble_sort.ltl)        | sorting, mutation                |
| Insertion Sort              | [`insertion_sort.ltl`](insertion_sort.ltl)  | sorting, insertion               |
| Quick Sort                  | [`quick_sort.ltl`](quick_sort.ltl)          | recursion, partitioning          |
| Merge Sort                  | [`merge_sort.ltl`](merge_sort.ltl)          | divide and conquer               |
| Greatest Common Divisor     | [`gcd.ltl`](gcd.ltl)                        | math, recursion                  |
| Factorial                   | [`factorial.ltl`](factorial.ltl)            | recursion/iteration              |
| Fibonacci                   | [`fibonacci.ltl`](fibonacci.ltl)            | sequence generation              |
| Collatz Conjecture          | [`collatz.ltl`](collatz.ltl)                | sequences, math                  |
| Perfect Numbers             | [`perfect_numbers.ltl`](perfect_numbers.ltl)| number theory                    |
| Happy Numbers               | [`happy_numbers.ltl`](happy_numbers.ltl)    | digit manipulation               |
| Narcissistic Numbers        | [`narcissistic_numbers.ltl`](narcissistic_numbers.ltl) | number theory           |
| Palindrome Detection        | [`palindrome.ltl`](palindrome.ltl)          | string operations                |
| Anagram Detection           | [`anagram.ltl`](anagram.ltl)                | sorting, hashing                 |
| Word Frequency              | [`word_frequency.ltl`](word_frequency.ltl)  | maps, string splitting           |
| Run-Length Encoding         | [`run_length.ltl`](run_length.ltl)          | compression, iteration           |
| Hex Dump                    | [`hex_dump.ltl`](hex_dump.ltl)              | formatting, binary               |
| Base64 Encode               | [`base64.ltl`](base64.ltl)                  | bitwise ops, codecs              |
| Matrix Multiplication       | [`matrix_multiply.ltl`](matrix_multiply.ltl) | 2D vectors, math                |
| Dot Product                 | [`dot_product.ltl`](dot_product.ltl)        | vector math                      |
| Prime Decomposition         | [`prime_decomposition.ltl`](prime_decomposition.ltl) | factors, number theory |
| Floyd's Triangle            | [`floyds_triangle.ltl`](floyds_triangle.ltl)| formatting, nested loops         |

## Dialect Notes

- All tasks use strict assertions (`assert_eq`) inside `main()` ensuring correct reference execution.
- Fully compatible with both the VM interpreter and the C backend (`lateralus c`).

## Verifying

Every file ends with `main()` that exercises the reference answer. No
external input required.

```sh
for f in examples/rosetta/*.ltl; do
  echo "== $f =="
  lateralus run "$f"
done
```

## Why Rosetta Code matters

Rosetta Code entries are a low-friction way for a language to show up
next to Python/Go/Rust/Haskell in side-by-side comparisons. They're also
small enough that a reviewer can read them in 30 seconds and form an
opinion.

If you want to port more tasks, see [`BOUNTIES.md`](../../BOUNTIES.md)
— "rosetta-20" is a $300 bounty for 20 additional canonical tasks.
