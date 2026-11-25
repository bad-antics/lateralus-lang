# Extended Euclidean Algorithm & Modular Inverses (Python → Lateralus Port)

Ports an idiomatic ~40-line Python reference computing extended Euclidean algorithm greatest common divisors and modular inverses over a prime Galois field ($\mathbb{Z}/p\mathbb{Z}$) to Lateralus, per the recurring port micro-bounty in `BOUNTIES.md`.

## The Problem

For given integers $a$ and modulus $m$, finding the modular multiplicative inverse $x \equiv a^{-1} \pmod m$ such that:
$$a \cdot x \equiv 1 \pmod m$$
is a foundational primitive across public-key cryptography (RSA, Diffie-Hellman, elliptic curve scalar multiplication) and finite field arithmetic. 

This benchmark computes modular inverses for the sequence $1 \le a \le N$ modulo prime $p = 1,000,000,007$ and accumulates their checksum. It stresses iterative quotient division, integer modulo, and state variable updates in a tight computational loop.

## Benchmark Results ($N = 100,000$, $p = 1,000,000,007$)

Tested on macOS Apple Silicon (Darwin 24):

| Implementation | Runtime | Speedup | Output Checksum |
| :--- | :--- | :--- | :--- |
| **Python 3.12 (CPython)** | **76.3 ms** | 1.0x (baseline) | `checksum=337069953` |
| **Lateralus (compiled via `lateralus c` + `-O3`)** | **1.2 ms** | **~63.5x faster** | `checksum=337069953` |

Both implementations produce identical modular checksum outputs across all test bounds ($N = 10, 100, 1000, 10000, 100000$).

## Running the Benchmark

```bash
# 1. Run Python reference
python3 examples/ports/egcd/egcd.py 100000 1000000007

# 2. Run Lateralus interpreter
lateralus run examples/ports/egcd/egcd.ltl

# 3. Transpile to C and run native binary
lateralus c examples/ports/egcd/egcd.ltl
clang -O3 egcd.c -o egcd_native
./egcd_native
```
