"""Find the maximum total payout of non-overlapping jobs."""

import sys
from bisect import bisect_right
from collections.abc import Iterable, Iterator
from operator import itemgetter
from typing import BinaryIO

Job = tuple[int, int, int]  # start, finish, payout
INT_MIN, INT_MAX = -(2**31), 2**31 - 1
MAX_JOBS = 1_000_000


def max_payout(jobs: Iterable[Job]) -> int:
    """Return the best payout for half-open jobs [start, finish), in any order."""
    finishes: list[int] = []
    best = [0]  # best[k] is the optimum over the first k jobs in finish order.
    for start, finish, payout in sorted(jobs, key=itemgetter(1)):
        compatible = bisect_right(finishes, start)
        best.append(max(best[-1], best[compatible] + payout))
        finishes.append(finish)
    return best[-1]


def read_jobs(stream: BinaryIO) -> Iterator[Job]:
    """Read a job count followed by that many start, finish and payout triples."""
    tokens = (token for line in stream for token in line.split())

    def read_int() -> int:
        token = next(tokens, b"")
        if not token or b"_" in token:
            raise ValueError("expected a decimal integer")
        if len(token) > 11:  # Ignore leading zeroes before converting an oversized token.
            sign = token[:1] if token[:1] in (b"+", b"-") else b""
            digits = token[len(sign) :]
            if not digits.isdigit():
                raise ValueError("expected a decimal integer")
            token = sign + (digits.lstrip(b"0") or b"0")
        value = int(token)
        if not INT_MIN <= value <= INT_MAX:
            raise ValueError("integer outside the signed 32-bit range")
        return value

    count = read_int()
    if not 0 <= count <= MAX_JOBS:
        raise ValueError(f"expected a job count between 0 and {MAX_JOBS}")
    for _ in range(count):
        start, finish, payout = read_int(), read_int(), read_int()
        if start >= finish:
            raise ValueError("each job must have a positive duration")
        yield start, finish, payout
    if next(tokens, None) is not None:
        raise ValueError("unexpected data after the last job")


if __name__ == "__main__":
    try:
        print(max_payout(read_jobs(sys.stdin.buffer)))
    except ValueError as error:
        print(f"Invalid input: {error}", file=sys.stderr)
        sys.exit(2)
