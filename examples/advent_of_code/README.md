# Advent of Code — Lateralus Solutions

Solutions are organized by year. Each file is self-contained: the
puzzle input is embedded as a multi-line string so `lateralus test`
self-verifies against the known answer.

## Why this exists

1. Onboarding bait: "AoC solutions in X language" is how half the
   world first encounters a new language.
2. Regression suite for stdlib: real puzzles exercise real code
   paths — parsing, hashing, search, number theory.
3. Showcases the niche: some of these problems are *trivial* if your
   stdlib already ships Aho-Corasick or Roaring bitmaps.

## Run

```sh
lateralus run examples/advent_of_code/2024/day01.ltl    # run with embedded input
lateralus test examples/advent_of_code/2024/day01.ltl   # verify answer
```

## Status

| Year | Days solved   | File                                        |
|------|---------------|---------------------------------------------|
| 2024 | 1, 2, 3       | [`2024/`](2024/)                            |
| 2023 | 1, 2, 3, 4, 5 | [`2023/`](2023/)                            |

Want to fill in the rest? See [`BOUNTIES.md`](../../BOUNTIES.md) — AoC-2024 complete set is a $500 bounty.
