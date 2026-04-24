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
