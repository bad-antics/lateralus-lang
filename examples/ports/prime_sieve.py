#!/usr/bin/env python3
"""Prime and twin-prime counter via the Sieve of Eratosthenes.

Idiomatic ~50-line Python reference for the Lateralus port bounty.
Prints two lines: the number of primes <= N, then the number of twin
prime pairs (p, p+2 both prime) <= N. Default N = 50,000,000.
"""
import sys
import time


def sieve(n):
    """Bytearray sieve: sieve[i] is 1 iff i is prime."""
    sieve = bytearray(b"\x01") * (n + 1)
    if n >= 0:
        sieve[0] = 0
    if n >= 1:
        sieve[1] = 0
    for p in range(2, int(n ** 0.5) + 1):
        if sieve[p]:
            start = p * p
            sieve[start::p] = b"\x00" * ((n - start) // p + 1)
    return sieve


def count_primes_and_twins(n):
    """Return (prime_count, twin_prime_pair_count) for primes <= n."""
    is_prime = sieve(n)
    prime_count = 0
    twin_count = 0
    prev_prime = -1
    for candidate in range(2, n + 1):
        if is_prime[candidate]:
            prime_count += 1
            if prev_prime >= 0 and candidate - prev_prime == 2:
                twin_count += 1
            prev_prime = candidate
    return prime_count, twin_count


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000_000
    start = time.time()
    primes, twins = count_primes_and_twins(n)
    elapsed = time.time() - start
    print(primes)
    print(twins)
    print(f"n={n} elapsed={elapsed:.3f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
