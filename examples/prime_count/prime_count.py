#!/usr/bin/env python3
"""Count the primes below a limit by trial division.

The classic textbook primality test: 2 is prime, even numbers above 2
are not, and every other candidate is tested against odd divisors up
to its square root. Simple, obviously correct, and slow enough in pure
Python that a compiled port wins by a wide margin.

Usage:
    python3 prime_count.py                 # primes below 1,000,000
    python3 prime_count.py --limit 100000

Expected output (default limit):
    primes below 1000000: 78498
"""

from __future__ import annotations

import argparse
import sys
import time


def is_prime(n: int) -> bool:
    """Return True if n is prime, using trial division by odd divisors."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def count_primes(limit: int) -> int:
    """Count the primes strictly below limit."""
    count = 0
    for n in range(2, limit):
        if is_prime(n):
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Count primes by trial division.")
    parser.add_argument("--limit", type=int, default=1_000_000,
                        help="count primes below LIMIT (default: 1000000)")
    args = parser.parse_args()

    start = time.perf_counter()
    count = count_primes(args.limit)
    elapsed = time.perf_counter() - start
    print(f"primes below {args.limit}: {count}")
    print(f"elapsed: {elapsed:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
