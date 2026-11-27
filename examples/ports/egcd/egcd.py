#!/usr/bin/env python3
"""
Extended Euclidean Algorithm and Modular Inverses Explorer in Python.
Used as the reference implementation for the Lateralus port.
"""

import sys
import time

def egcd(a: int, b: int) -> tuple[int, int]:
    x0, x1 = 1, 0
    curr_a, curr_b = a, b
    while curr_b != 0:
        q = curr_a // curr_b
        curr_a, curr_b = curr_b, curr_a % curr_b
        x0, x1 = x1, x0 - q * x1
    return curr_a, x0

def mod_inv(a: int, m: int) -> int:
    g, x = egcd(a, m)
    if g != 1:
        return -1
    res = x % m
    if res < 0:
        res += m
    return res

def sum_inverses(limit: int, modulus: int) -> int:
    total = 0
    for i in range(1, limit + 1):
        inv = mod_inv(i, modulus)
        if inv != -1:
            total = (total + inv) % modulus
    return total

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    modulus = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000007
    t0 = time.perf_counter()
    res = sum_inverses(limit, modulus)
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"limit={limit} modulus={modulus} checksum={res} elapsed_ms={elapsed:.2f}")

if __name__ == "__main__":
    main()
