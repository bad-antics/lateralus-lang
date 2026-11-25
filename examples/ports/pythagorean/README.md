# Counting integer right triangles by perimeter

The Python reference and its Lateralus port print the number of different integer right triangles with perimeter at most each of six limits. Swapping the legs counts as the same triangle. At a bound of 24, both (3, 4, 5) and (6, 8, 10) qualify. A bound of 120 admits 22 triangles in total.

Both programs enumerate coprime integers `m > n > 0` of opposite parity. Each pair describes one primitive triangle with perimeter `p = 2m(m + n)`. Exactly `floor(limit / p)` positive multiples of that triangle fit. Two different pairs may have the same perimeter, so each pair contributes separately.

| Inclusive limit | Triangle count |
| ---: | ---: |
| 11 | 0 |
| 12 | 1 |
| 24 | 2 |
| 120 | 22 |
| 1,000 | 325 |
| 10,000,000 | 9,706,567 |

## Build and compare

From this directory, with the repository's Lateralus CLI on PATH and a C99 compiler installed:

```sh
lateralus c triples.ltl -o triples.c
cc -std=c99 -O2 triples.c -o triples
python3 triples.py > reference.txt
./triples > native.txt
diff -u reference.txt native.txt
```

To measure end-to-end wall time, compile once and time each executable on the full set of limits. For example, with Hyperfine installed:

```sh
hyperfine --warmup 1 --runs 9 'python3 triples.py' './triples'
```

The repository test independently enumerates triangle sides for every bound through 240 and checks the native binary's output against the reference.
