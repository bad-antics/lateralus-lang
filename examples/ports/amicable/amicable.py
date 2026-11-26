"""Amicable Numbers pair count and sum below upper bound — idiomatic Python."""
import sys


def sum_proper_divisors(n: int) -> int:
    """Return the sum of positive proper divisors of n."""
    if n <= 1:
        return 0
    total = 1
    d = 2
    while d * d <= n:
        if n % d == 0:
            total += d
            other = n // d
            if other != d:
                total += other
        d += 1
    return total


def amicable_summary(upper: int) -> tuple[int, int]:
    """Return (pairs, total_sum) for all amicable pairs (a < b < upper)."""
    pairs = 0
    total_sum = 0
    a = 2
    while a < upper:
        b = sum_proper_divisors(a)
        if b > a and b < upper and sum_proper_divisors(b) == a:
            pairs += 1
            total_sum += a + b
        a += 1
    return pairs, total_sum


def main() -> None:
    upper = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    pairs, total_sum = amicable_summary(upper)
    print(f"upper={upper} pairs={pairs} sum={total_sum}")


if __name__ == "__main__":
    main()
