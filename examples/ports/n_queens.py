#!/usr/bin/env python3
"""N-Queens solution counter — idiomatic ~50-line Python reference.

Counts the number of ways to place n non-attacking queens on an n x n
board using the classic bitmask backtracking formulation. Prints the
count for n = 13 (73,712 solutions).
"""
import sys
import time


def count_queens(n, cols, diag_l, diag_r):
    """cols: occupied columns; diag_l/diag_r: attacked diagonals."""
    if cols == (1 << n) - 1:
        return 1
    total = 0
    free = ~(cols | diag_l | diag_r) & ((1 << n) - 1)
    while free:
        bit = free & -free          # lowest free column
        free &= free - 1
        total += count_queens(
            n,
            cols | bit,
            (diag_l | bit) << 1,    # left diagonal shifts left
            (diag_r | bit) >> 1,    # right diagonal shifts right
        )
    return total


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    start = time.perf_counter()
    solutions = count_queens(n, 0, 0, 0)
    elapsed = time.perf_counter() - start
    print(f"n={n} solutions={solutions} time={elapsed:.3f}s")


if __name__ == "__main__":
    main()
