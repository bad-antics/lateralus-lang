"""Count distinct integer right triangles with perimeter at most a given limit.

A triangle and its reflection are counted once. Different triangles with
the same perimeter count separately. Run this file to print cumulative
counts for the same limits used in the Lateralus example.
"""

from collections.abc import Iterator
from math import gcd

# The first three bounds bracket the first primitive triangle and its double.
LIMITS = (11, 12, 24, 120, 1000, 10_000_000)


def primitive_perimeters(limit: int) -> Iterator[int]:
    """Yield a perimeter for each primitive triangle within the bound.

    Euclid's parameters m > n > 0 yield exactly one representative per
    primitive triangle when m and n are coprime and of opposite parity.
    The legs are m² - n² and 2mn, and the hypotenuse is m² + n².
    Their sum is 2m(m + n).
    """
    # Even the smallest possible n is 1, so larger m can be ruled out early.
    m = 2
    while 2 * m * (m + 1) <= limit:
        # n starts at 1 for even m and at 2 for odd m.
        for n in range(1 + m % 2, m, 2):
            perimeter = 2 * m * (m + n)
            if perimeter > limit:
                break
            if gcd(m, n) == 1:
                yield perimeter
        m += 1


def count_triangles(limit: int) -> int:
    """Count all positive integer multiples of the primitive triangles."""
    # Keep repeated primitive perimeters: each belongs to a distinct triangle
    # and contributes its own family of scaled solutions.
    return sum(limit // p for p in primitive_perimeters(limit))


def main() -> None:
    """Print counts in ascending order of perimeter limit."""
    for limit in LIMITS:
        print(count_triangles(limit))


if __name__ == "__main__":
    main()
