#!/usr/bin/env python3
"""
Fast Modular Exponentiation and Deterministic Miller-Rabin Primality Test in Python.
Used as the reference implementation for the Lateralus port.
"""

import sys
import time

def power(base: int, exp: int, mod: int) -> int:
    res = 1
    base %= mod
    while exp > 0:
        if exp % 2 == 1:
            res = (res * base) % mod
        base = (base * base) % mod
        exp //= 2
    return res

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    bases = (2, 3, 5, 7, 11, 13, 17)
    for a in bases:
        if n <= a:
            break
        x = power(a, d, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                composite = False
                break
        if composite:
            return False
    return True

def count_primes(limit: int) -> int:
    count = 0
    for i in range(1, limit + 1):
        if is_prime(i):
            count += 1
    return count

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    t0 = time.perf_counter()
    res = count_primes(limit)
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"limit={limit} pi={res} elapsed_ms={elapsed:.2f}")

if __name__ == "__main__":
    main()
