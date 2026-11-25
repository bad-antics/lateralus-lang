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
| Base64 Encode/Decode        | [`base64.ltl`](base64.ltl)                  | codecs, bit manipulation         |
| SHA-256 Hash                | [`sha256.ltl`](sha256.ltl)                  | cryptography, hashes             |
| MD5 Hash                    | [`md5.ltl`](md5.ltl)                        | cryptography, hashes             |
| URL Encoding                | [`url_encoding.ltl`](url_encoding.ltl)      | codecs, escaping                 |
| Hamming Distance            | [`hamming.ltl`](hamming.ltl)                | string search, distance          |
| Soundex                     | [`soundex.ltl`](soundex.ltl)                | phonetic algorithm, search       |
| ROT13                       | [`rot13.ltl`](rot13.ltl)                    | codecs, substitution cipher      |
| Run-length Encoding         | [`rle.ltl`](rle.ltl)                        | compression, codecs              |
| Binary Search               | [`binary_search.ltl`](binary_search.ltl)    | search, algorithms               |
| QuickSort                   | [`quicksort.ltl`](quicksort.ltl)            | sorting, divide and conquer      |
| MergeSort                   | [`mergesort.ltl`](mergesort.ltl)            | sorting, divide and conquer      |
| Anagrams                    | [`anagrams.ltl`](anagrams.ltl)              | string grouping, search          |
| Longest Common Subsequence  | [`lcs.ltl`](lcs.ltl)                        | dynamic programming              |
| Amicable Pairs              | [`amicable.ltl`](amicable.ltl)              | number theory                    |
| Ackermann Function          | [`ackermann.ltl`](ackermann.ltl)            | recursion                        |
| Factors of an Integer       | [`factors.ltl`](factors.ltl)                | number theory                    |
| Haversine Formula           | [`haversine.ltl`](haversine.ltl)            | geometry, math                   |
| Palindrome Check            | [`palindrome.ltl`](palindrome.ltl)          | string inspection                |
| ISBN-10 Check               | [`isbn10.ltl`](isbn10.ltl)                  | checksum verification            |
| ISBN-13 Check               | [`isbn13.ltl`](isbn13.ltl)                  | checksum verification            |

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
