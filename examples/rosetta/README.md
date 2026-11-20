# Rosetta Code — Lateralus Implementations

Canonical programming tasks implemented in Lateralus. Each file is a
self-contained `.ltl` you can run with `lateralus run <file>`.

These are deliberate ports of tasks that appear on
[rosettacode.org](https://rosettacode.org) — useful both as a comparative
reference and as discoverability ("Rosetta Code in X" searches).
Every row links to the Rosetta task page it corresponds to.

## Tasks

| Task | File | Rosetta task | Showcases |
|------|------|--------------|-----------|
| FizzBuzz | [`fizzbuzz.ltl`](fizzbuzz.ltl) | [FizzBuzz](https://rosettacode.org/wiki/FizzBuzz) | control flow |
| Luhn Checksum | [`luhn.ltl`](luhn.ltl) | [Luhn test of credit card numbers](https://rosettacode.org/wiki/Luhn_test_of_credit_card_numbers) | digit arithmetic, integer mod |
| Levenshtein Distance | [`levenshtein.ltl`](levenshtein.ltl) | [Levenshtein distance](https://rosettacode.org/wiki/Levenshtein_distance) | 2-D dp, string distance |
| Roman Numerals (to/from) | [`roman.ltl`](roman.ltl) | [Roman numerals](https://rosettacode.org/wiki/Roman_numerals) | table-driven conversion |
| Sieve of Eratosthenes | [`sieve.ltl`](sieve.ltl) | [Sieve of Eratosthenes](https://rosettacode.org/wiki/Sieve_of_Eratosthenes) | list mutation, number theory |
| Caesar Cipher | [`caesar.ltl`](caesar.ltl) | [Caesar cipher](https://rosettacode.org/wiki/Caesar_cipher) | char arithmetic |
| 0/1 Knapsack | [`knapsack.ltl`](knapsack.ltl) | [Knapsack problem/0-1](https://rosettacode.org/wiki/Knapsack_problem/0-1) | dynamic programming |
| N-Queens | [`nqueens.ltl`](nqueens.ltl) | [N-queens problem](https://rosettacode.org/wiki/N-queens_problem) | recursion + backtracking |
| Topological Sort | [`topological_sort.ltl`](topological_sort.ltl) | [Topological sort](https://rosettacode.org/wiki/Topological_sort) | graphs, Kahn's algorithm |
| Huffman Coding | [`huffman.ltl`](huffman.ltl) | [Huffman coding](https://rosettacode.org/wiki/Huffman_coding) | trees + greedy |
| JSON Mini Parser | [`json_mini.ltl`](json_mini.ltl) | [JSON](https://rosettacode.org/wiki/JSON) | recursive-descent parsing |
| 100 Doors | [`one_hundred_doors.ltl`](one_hundred_doors.ltl) | [100 doors](https://rosettacode.org/wiki/100_doors) | boolean toggling |
| Binary Search | [`binary_search.ltl`](binary_search.ltl) | [Binary search](https://rosettacode.org/wiki/Binary_search) | halving search |
| Bubble Sort | [`bubble_sort.ltl`](bubble_sort.ltl) | [Sorting algorithms/Bubble sort](https://rosettacode.org/wiki/Sorting_algorithms/Bubble_sort) | in-place swaps |
| Insertion Sort | [`insertion_sort.ltl`](insertion_sort.ltl) | [Sorting algorithms/Insertion sort](https://rosettacode.org/wiki/Sorting_algorithms/Insertion_sort) | shifting insertion |
| Quicksort | [`quicksort.ltl`](quicksort.ltl) | [Sorting algorithms/Quicksort](https://rosettacode.org/wiki/Sorting_algorithms/Quicksort) | divide & conquer |
| Merge Sort | [`merge_sort.ltl`](merge_sort.ltl) | [Sorting algorithms/Merge sort](https://rosettacode.org/wiki/Sorting_algorithms/Merge_sort) | stable merge |
| Greatest Common Divisor | [`greatest_common_divisor.ltl`](greatest_common_divisor.ltl) | [Greatest common divisor](https://rosettacode.org/wiki/Greatest_common_divisor) | Euclid's algorithm |
| Factorial | [`factorial.ltl`](factorial.ltl) | [Factorial](https://rosettacode.org/wiki/Factorial) | recursion + big ints |
| Fibonacci Sequence | [`fibonacci_sequence.ltl`](fibonacci_sequence.ltl) | [Fibonacci sequence](https://rosettacode.org/wiki/Fibonacci_sequence) | iterative accumulation |
| Collatz Sequence | [`collatz_sequence.ltl`](collatz_sequence.ltl) | [Collatz sequence](https://rosettacode.org/wiki/Collatz_sequence) | termination search |
| Perfect Numbers | [`perfect_numbers.ltl`](perfect_numbers.ltl) | [Perfect numbers](https://rosettacode.org/wiki/Perfect_numbers) | divisor enumeration |
| Happy Numbers | [`happy_numbers.ltl`](happy_numbers.ltl) | [Happy numbers](https://rosettacode.org/wiki/Happy_numbers) | digit sums, cycles |
| Narcissistic Numbers | [`narcissistic_numbers.ltl`](narcissistic_numbers.ltl) | [Narcissistic numbers](https://rosettacode.org/wiki/Narcissistic_numbers) | digit decomposition |
| Palindrome Detection | [`palindrome_detection.ltl`](palindrome_detection.ltl) | [Palindrome detection](https://rosettacode.org/wiki/Palindrome_detection) | normalisation, two-pointer |
| Anagram Detection | [`anagram_detection.ltl`](anagram_detection.ltl) | [Anagram detection](https://rosettacode.org/wiki/Anagram_detection) | string fingerprints |
| Word Frequency | [`word_frequency.ltl`](word_frequency.ltl) | [Word frequency](https://rosettacode.org/wiki/Word_frequency) | maps + sorting |
| Run-Length Encoding | [`run_length_encoding.ltl`](run_length_encoding.ltl) | [Run-length encoding](https://rosettacode.org/wiki/Run-length_encoding) | codec, flag-driven loops |
| Hex Dump | [`hex_dump.ltl`](hex_dump.ltl) | [Hex dump](https://rosettacode.org/wiki/Hex_dump) | byte formatting |
| Base64 Encode | [`base64_encode.ltl`](base64_encode.ltl) | [Base64 encode](https://rosettacode.org/wiki/Base64_encode) | 6-bit packing |
| Matrix Multiplication | [`matrix_multiplication.ltl`](matrix_multiplication.ltl) | [Matrix multiplication](https://rosettacode.org/wiki/Matrix_multiplication) | nested lists |
| Dot Product | [`dot_product.ltl`](dot_product.ltl) | [Dot product](https://rosettacode.org/wiki/Dot_product) | numeric folds |
| Prime Decomposition | [`prime_decomposition.ltl`](prime_decomposition.ltl) | [Prime decomposition](https://rosettacode.org/wiki/Prime_decomposition) | factorisation |
| Floyd's Triangle | [`floyds_triangle.ltl`](floyds_triangle.ltl) | [Floyd's triangle](https://rosettacode.org/wiki/Floyd%27s_triangle) | nested row printing |

## Verifying

Every file ends with `main()` that exercises the reference answer and
asserts it with `assert_eq`, so a wrong port fails loudly instead of
printing plausible-looking output. No external input required.

```sh
for f in examples/rosetta/*.ltl; do
  echo "== $f =="
  lateralus run "$f"
done
```

## Dialect notes

Porting these tasks exercises a few spots where Lateralus differs from
the languages Rosetta readers arrive from:

- `/` is float division. Use `idiv(a, b)` for truncating integer
  division and `imod(a, b)` for the remainder — otherwise list indices
  come back as floats.
- There is no `break`/`continue`. Early exit from a loop is a boolean
  flag (`let alive = true; while alive { ... alive = false }`).
- Comparing single characters with `>= "a"` is not reliable; use the
  numeric range on `ord(c)` (97–122 lowercase, 48–57 digits).

## Why Rosetta Code matters

Rosetta Code entries are a low-friction way for a language to show up
next to Python/Go/Rust/Haskell in side-by-side comparisons. They're also
small enough that a reviewer can read them in 30 seconds and form an
opinion.

If you want to port more tasks, see [`BOUNTIES.md`](../../BOUNTIES.md)
— "rosetta-20" is a $150 bounty for 20 additional canonical tasks.
