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
| MD4 Hash                    | [`md4.ltl`](md4.ltl)                        | cryptographic hash               |
| MD5 Hash                    | [`md5.ltl`](md5.ltl)                        | cryptographic hash               |
| SHA-1 Hash                  | [`sha1.ltl`](sha1.ltl)                      | cryptographic hash               |
| SHA-256 Hash                | [`sha256.ltl`](sha256.ltl)                    | cryptographic hash               |
| CRC-32                      | [`crc32.ltl`](crc32.ltl)                    | checksum                         |
| Damm Algorithm              | [`damm.ltl`](damm.ltl)                      | check digit algorithm            |
| Base64 Decode               | [`base64_decode.ltl`](base64_decode.ltl)    | codec                            |
| URL Encoding                | [`url_encode.ltl`](url_encode.ltl)          | codec                            |
| URL Decoding                | [`url_decode.ltl`](url_decode.ltl)          | codec                            |
| UTF-8 Encode & Decode       | [`utf8.ltl`](utf8.ltl)                      | character encoding               |
| Variable-Length Quantity    | [`vlq.ltl`](vlq.ltl)                        | variable-length packing          |
| LZW Compression             | [`lzw.ltl`](lzw.ltl)                        | compression                      |
| Burrows-Wheeler Transform   | [`bwt.ltl`](bwt.ltl)                        | block sorting transform          |
| Move-to-Front               | [`mtf.ltl`](mtf.ltl)                        | transform                        |
| Vigenère Cipher             | [`vigenere.ltl`](vigenere.ltl)              | classical cipher                 |
| CSV to HTML                 | [`csv_to_html.ltl`](csv_to_html.ltl)        | data format translation          |
| Tokenize with Escaping      | [`tokenize_escape.ltl`](tokenize_escape.ltl)| string parsing                   |
| Balanced Brackets           | [`balanced_brackets.ltl`](balanced_brackets.ltl)| syntax validation            |
| Longest Common Substring    | [`lcs_string.ltl`](lcs_string.ltl)          | string search                    |
| Longest Common Subsequence  | [`lcs_sequence.ltl`](lcs_sequence.ltl)      | sequence search                  |

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
