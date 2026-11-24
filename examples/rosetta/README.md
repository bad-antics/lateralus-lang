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

### Added in the 2026-11 expansion (15 tasks)

| Task | File | Rosetta page |
|------|------|--------------|
| Fibonacci sequence | [`fibonacci.ltl`](fibonacci.ltl) | https://rosettacode.org/wiki/Fibonacci_sequence |
| Greatest common divisor | [`gcd.ltl`](gcd.ltl) | https://rosettacode.org/wiki/Greatest_common_divisor |
| Binary search | [`binary_search.ltl`](binary_search.ltl) | https://rosettacode.org/wiki/Binary_search |
| Palindrome detection | [`palindrome.ltl`](palindrome.ltl) | https://rosettacode.org/wiki/Palindrome_detection |
| Sorting (stdlib) | [`sorting_stdlib.ltl`](sorting_stdlib.ltl) | https://rosettacode.org/wiki/Sorting_algorithms/Quicksort |
| Sorting (insertion) | [`sorting_insertion.ltl`](sorting_insertion.ltl) | https://rosettacode.org/wiki/Sorting_algorithms/Insertion_sort |
| Sorting (quicksort, recursive) | [`sorting_quicksort.ltl`](sorting_quicksort.ltl) | https://rosettacode.org/wiki/Sorting_algorithms/Quicksort |
| Base64 alphabet | [`base64_alphabet.ltl`](base64_alphabet.ltl) | https://rosettacode.org/wiki/Base64_encode_data |
| SHA-256 | [`sha256.ltl`](sha256.ltl) | https://rosettacode.org/wiki/SHA-256 |
| Word frequency | [`word_frequency.ltl`](word_frequency.ltl) | https://rosettacode.org/wiki/Word_frequency |
| Reverse a string | [`reverse_string.ltl`](reverse_string.ltl) | https://rosettacode.org/wiki/Reverse_a_string |
| Leap year | [`leap_year.ltl`](leap_year.ltl) | https://rosettacode.org/wiki/Leap_year |
| Factorial | [`factorial.ltl`](factorial.ltl) | https://rosettacode.org/wiki/Factorial |
| Collatz sequence | [`collatz.ltl`](collatz.ltl) | https://rosettacode.org/wiki/Collatz_sequence |
| Sum of squares | [`sum_of_squares.ltl`](sum_of_squares.ltl) | https://rosettacode.org/wiki/Sum_of_squares |

Every file above ends with a self-check that prints `OK` when it passes, so
`for f in examples/rosetta/*.ltl; do lateralus run "$f"; done` can be used as a
smoke suite. Two languages quirks worth knowing when porting more tasks:
string literals beginning with `{` hit the f-string translation path (build
braces with `chr(123)`/`chr(125)`), and module imports only resolve for the
registered stdlib subset (`stdlib.strings`, `stdlib.collections`, ...).
