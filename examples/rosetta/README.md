# Rosetta Code — Lateralus Implementations

Canonical programming tasks implemented in Lateralus. Each file is a
self-contained `.ltl` you can run with `lateralus run <file>`.

These are deliberate ports of tasks that appear on
[rosettacode.org](https://rosettacode.org) — useful both as a comparative
reference and as discoverability ("Rosetta Code in X" searches).

## Tasks

Every entry links to the Rosetta Code task it implements.

### Hashes and checksums

| Task | File | Checked against |
|------|------|-----------------|
| [MD4](https://rosettacode.org/wiki/MD4) | [`md4.ltl`](md4.ltl) | task string + RFC 1320 A.5 suite |
| [MD5](https://rosettacode.org/wiki/MD5) | [`md5.ltl`](md5.ltl) | task string + RFC 1321 A.5 suite |
| [SHA-1](https://rosettacode.org/wiki/SHA-1) | [`sha_1.ltl`](sha_1.ltl) | task string + FIPS 180 / RFC 3174 vectors |
| [SHA-256](https://rosettacode.org/wiki/SHA-256) | [`sha_256.ltl`](sha_256.ltl) | task string + FIPS 180 vectors (empty, `abc`, two-block) |
| [CRC-32](https://rosettacode.org/wiki/CRC-32) | [`crc_32.ltl`](crc_32.ltl) | task string, `123456789` check value, empty input |
| [Damm algorithm](https://rosettacode.org/wiki/Damm_algorithm) | [`damm_algorithm.ltl`](damm_algorithm.ltl) | the four task numbers, check-digit generation, every adjacent transposition |
| [Luhn test of credit card numbers](https://rosettacode.org/wiki/Luhn_test_of_credit_card_numbers) | [`luhn.ltl`](luhn.ltl) | task numbers |

### Codecs and ciphers

| Task | File | Checked against |
|------|------|-----------------|
| [Base64 decode data](https://rosettacode.org/wiki/Base64_decode_data) | [`base64_decode.ltl`](base64_decode.ltl) | task quotation, RFC 4648 §10 vectors (encode + decode), binary round trip, invalid input |
| [URL encoding](https://rosettacode.org/wiki/URL_encoding) | [`url_encoding.ltl`](url_encoding.ltl) | task example, RFC 3986 variant, UTF-8 input |
| [URL decoding](https://rosettacode.org/wiki/URL_decoding) | [`url_decoding.ltl`](url_decoding.ltl) | all three task examples, 4-byte UTF-8, stray `%` |
| [UTF-8 encode and decode](https://rosettacode.org/wiki/UTF-8_encode_and_decode) | [`utf8_encode_decode.ltl`](utf8_encode_decode.ltl) | task table, length boundaries, malformed sequences |
| [Variable-length quantity](https://rosettacode.org/wiki/Variable-length_quantity) | [`variable_length_quantity.ltl`](variable_length_quantity.ltl) | task values + MIDI spec table, malformed sequences |
| [LZW compression](https://rosettacode.org/wiki/LZW_compression) | [`lzw_compression.ltl`](lzw_compression.ltl) | task code sequence, cScSc case, round trips, corrupt stream |
| [Burrows–Wheeler transform](https://rosettacode.org/wiki/Burrows%E2%80%93Wheeler_transform) | [`burrows_wheeler_transform.ltl`](burrows_wheeler_transform.ltl) | all five task strings, forward + inverse |
| [Move-to-front algorithm](https://rosettacode.org/wiki/Move-to-front_algorithm) | [`move_to_front.ltl`](move_to_front.ltl) | all three task words, encode + decode |
| [Vigenère cipher](https://rosettacode.org/wiki/Vigen%C3%A8re_cipher) | [`vigenere_cipher.ltl`](vigenere_cipher.ltl) | task text and key, `ATTACKATDAWN` / `LEMON` |
| [Caesar cipher](https://rosettacode.org/wiki/Caesar_cipher) | [`caesar.ltl`](caesar.ltl) | round trip |
| [Huffman coding](https://rosettacode.org/wiki/Huffman_coding) | [`huffman.ltl`](huffman.ltl) | task sentence |

### Formats and parsing

| Task | File | Checked against |
|------|------|-----------------|
| [CSV to HTML translation](https://rosettacode.org/wiki/CSV_to_HTML_translation) | [`csv_to_html.ltl`](csv_to_html.ltl) | task CSV, exact HTML output (header extra credit), escaping |
| [Tokenize a string with escaping](https://rosettacode.org/wiki/Tokenize_a_string_with_escaping) | [`tokenize_with_escaping.ltl`](tokenize_with_escaping.ltl) | task input/output, empty and edge fields |
| [Balanced brackets](https://rosettacode.org/wiki/Balanced_brackets) | [`balanced_brackets.ltl`](balanced_brackets.ltl) | fixed cases + seeded random strings cross-checked by a second algorithm |
| [JSON](https://rosettacode.org/wiki/JSON) | [`json_mini.ltl`](json_mini.ltl) | parse + re-serialise a sample document |
| [Roman numerals/Encode](https://rosettacode.org/wiki/Roman_numerals/Encode) | [`roman.ltl`](roman.ltl) | round trips |

### Search and string algorithms

| Task | File | Checked against |
|------|------|-----------------|
| [Longest common substring](https://rosettacode.org/wiki/Longest_common_substring) | [`longest_common_substring.ltl`](longest_common_substring.ltl) | task pair, substring vs subsequence, no-match / empty / identical |
| [Longest common subsequence](https://rosettacode.org/wiki/Longest_common_subsequence) | [`longest_common_subsequence.ltl`](longest_common_subsequence.ltl) | task pairs, CLRS example, result is a real subsequence of both |
| [Levenshtein distance](https://rosettacode.org/wiki/Levenshtein_distance) | [`levenshtein.ltl`](levenshtein.ltl) | task pair |
| [Topological sort](https://rosettacode.org/wiki/Topological_sort) | [`topological_sort.ltl`](topological_sort.ltl) | dressing-order graph |

### Other

| Task | File | Showcases |
|------|------|-----------|
| [FizzBuzz](https://rosettacode.org/wiki/FizzBuzz) | [`fizzbuzz.ltl`](fizzbuzz.ltl) | control flow |
| [Sieve of Eratosthenes](https://rosettacode.org/wiki/Sieve_of_Eratosthenes) | [`sieve.ltl`](sieve.ltl) | list mutation, number theory |
| [Knapsack problem/0-1](https://rosettacode.org/wiki/Knapsack_problem/0-1) | [`knapsack.ltl`](knapsack.ltl) | dynamic programming |
| [N-queens problem](https://rosettacode.org/wiki/N-queens_problem) | [`nqueens.ltl`](nqueens.ltl) | recursion + backtracking |

## Verifying

Every file ends with `main()` that exercises the reference answers. No
external input is required, and the hash, codec, format and search ports
check themselves with `assert_eq` / `assert_true`, so a wrong answer exits
non-zero instead of printing a plausible-looking result.

```sh
for f in examples/rosetta/*.ltl; do
  echo "== $f =="
  lateralus run "$f"
done
```

The same check runs in CI through `tests/test_rosetta_examples.py`:

```sh
pytest tests/test_rosetta_examples.py -q
```

Expected values were taken from the Rosetta task pages and the primary
specifications named above (RFC 1320, RFC 1321, RFC 3174, RFC 4648,
FIPS 180-4, the CRC catalogue, the MIDI VLQ table), and cross-checked
against Python's `hashlib`, `zlib`, `base64` and `urllib.parse` where those
cover the algorithm. All implementations are written from scratch in
Lateralus; none call into a host-language crypto or codec library.

## Why Rosetta Code matters

Rosetta Code entries are a low-friction way for a language to show up
next to Python/Go/Rust/Haskell in side-by-side comparisons. They're also
small enough that a reviewer can read them in 30 seconds and form an
opinion.

If you want to port more tasks, see [`BOUNTIES.md`](../../BOUNTIES.md)
— "rosetta-20" is the bounty for 20 additional canonical tasks.
