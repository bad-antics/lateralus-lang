"""
Collatz Hailstone Max-Sequence Explorer (Python Reference).
Computes the starting integer n <= limit that produces the longest Collatz chain.
"""

import sys
import time

def collatz_len(n: int) -> int:
    steps = 1
    curr = n
    while curr > 1:
        if curr % 2 == 0:
            curr = curr // 2
        else:
            curr = 3 * curr + 1
        steps += 1
    return steps

def max_collatz_under(limit: int):
    max_len = 0
    best_start = 1
    for i in range(1, limit + 1):
        l = collatz_len(i)
        if l > max_len:
            max_len = l
            best_start = i
    return best_start, max_len

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    t0 = time.perf_counter()
    start, length = max_collatz_under(limit)
    t1 = time.perf_counter()
    print(f"limit={limit} best_start={start} length={length} time={(t1 - t0)*1000:.2f}ms")
