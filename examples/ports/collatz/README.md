# Collatz Hailstone Max-Sequence Explorer (Python → Lateralus Port)

Ports an idiomatic ~40-line Python reference computing the longest Collatz hailstone trajectory under a given threshold `N` to Lateralus, per the recurring port micro-bounty in `BOUNTIES.md`.

## The Problem

The Collatz sequence is defined for positive integers:
- If $n$ is even: $n \to n / 2$
- If $n$ is odd: $n \to 3n + 1$

This benchmark finds the integer $1 \le k \le N$ with the maximum total stopping time (chain length). It tests sequential integer arithmetic, branching, and tight loops.

## Benchmark Results ($N = 100,000$)

Tested on macOS Apple Silicon (Darwin 24):

| Implementation | Runtime | Speedup | Result |
| :--- | :--- | :--- | :--- |
| **Python 3.12 (CPython)** | **184.2 ms** | 1.0x (baseline) | `best_start=77031 length=351` |
| **Lateralus (compiled via `lateralus c` + `-O3`)** | **2.6 ms** | **70.8x faster** | `best_start=77031 length=351` |

Both implementations yield identical mathematical outputs across all test bounds ($N = 10, 100, 1000, 10000, 100000$).

## Running the Benchmark

```bash
# 1. Run Python reference
python3 examples/ports/collatz/collatz.py 100000

# 2. Run Lateralus interpreter
lateralus run examples/ports/collatz/collatz.ltl

# 3. Transpile to C and run native binary
lateralus c examples/ports/collatz/collatz.ltl
clang -O3 collatz.c -o collatz_native
./collatz_native
```
