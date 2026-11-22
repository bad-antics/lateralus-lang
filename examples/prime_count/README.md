# prime_count — trial-division prime counting, Python vs Lateralus

A port of an idiomatic 50-line Python program to Lateralus, for the
`$25` port micro-bounty in [`BOUNTIES.md`](../../BOUNTIES.md).

## The program

Count the primes strictly below 1,000,000 by trial division: 2 is
prime, even numbers above 2 are not, and every other candidate is
tested against odd divisors up to its square root. The Python original
and the Lateralus port implement the same algorithm, so the comparison
is apples-to-apples.

Expected answer (both programs): **78,498** primes below 1,000,000.

## Files

| File | What it is |
| --- | --- |
| [`prime_count.py`](prime_count.py) | The Python original (~50 lines) |
| [`prime_count.ltl`](prime_count.ltl) | The Lateralus port |
| [`benchmark.py`](benchmark.py) | Timing harness (median of N runs) |

## Run it

```sh
# Python original
python3 prime_count.py
# primes below 1000000: 78498

# Lateralus, interpreted
lateralus run prime_count.ltl
# 78498

# Lateralus, compiled to a native binary
lateralus c prime_count.ltl -o prime_count.c
gcc -O2 -o prime_count prime_count.c -lm
./prime_count
# 78498
```

The Lateralus program prints the bare count, the same style as
`benchmarks/src/sieve.ltl`. The C backend cannot yet compile string
interpolation (`"...{x}..."`) or `str(int)`, so the label
(`primes below 1000000: `) lives in the Python original, not in the
`.ltl` output.

## Benchmark

`python3 benchmark.py` builds the C binary and times both programs at
the default limit (median of 5 runs each, Linux VM, 2026-11-23):

| Program | Median wall time | Min wall time |
| --- | --- | --- |
| Python 3.12 (`prime_count.py`) | 5.31 s | 5.00 s |
| Lateralus, compiled (`lateralus c` + `gcc -O2`) | 0.253 s | 0.213 s |

**Speedup: 21.0x faster** (median wall time). Both programs print
78,498.

## Verification

```sh
lateralus check prime_count.ltl          # type-check: OK
# interpreter, small limit (edit LIMIT to 1000 in a temp copy)
lateralus run prime_count.ltl            # full limit, interpreted
./prime_count                            # compiled binary: 78498
python3 prime_count.py --limit 1000      # 168, matches the port
python3 prime_count.py --limit 100       # 25,  matches the port
```

Notes:

- There are no `@test` blocks in `prime_count.ltl`: the C backend
  emits calls to `assert_true` / `assert_eq` that have no definition
  in the generated C, so a file with `@test` blocks cannot compile
  with `lateralus c`. Verification is by the runs above instead.
- `lateralus test` itself is currently broken repo-wide
  (`AttributeError: 'CompileResult' object has no attribute 'code'`
  in `__main__.py`, reproduced on `examples/showcase.ltl` too), so it
  was not used for verification. That is a separate toolchain bug,
  not something this port depends on.
- `lateralus fmt` and `lateralus lint --strict` were not used either:
  `fmt` rewrites `return false` to `return false,` and destroys
  indentation; `lint --strict` crashes with an `AttributeError`.
  Both are pre-existing toolchain bugs, unrelated to this port.
