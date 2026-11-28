"""
LATERALUS Standard Library — radix_sort
Python implementation of stdlib/radix_sort.ltl

Bit-for-bit mirror of the Lateralus non-comparison sorts. Used as the
runtime backing for `import radix_sort` in transpiled Lateralus code
(see codegen/python.py alias map).
"""
from __future__ import annotations

MASK32 = 0xFFFFFFFF


def counting_sort(xs, k: int) -> list:
    """Stable counting sort over nonneg ints with known upper bound k."""
    counts = [0] * (k + 1)
    for v in xs:
        counts[v] = counts[v] + 1
    out: list = []
    for v in range(k + 1):
        out = out + [v] * counts[v]
    return out


def _radix_pass(xs, shift: int) -> list:
    # 256-way bucket sort on one byte.
    buckets: list = [[] for _ in range(256)]
    for v in xs:
        buckets[(v >> shift) & 0xFF] = buckets[(v >> shift) & 0xFF] + [v]
    out: list = []
    for b in range(256):
        out = out + buckets[b]
    return out


def radix_sort_u32(xs) -> list:
    """LSD byte radix sort for 32-bit unsigned ints."""
    xs = _radix_pass(list(xs), 0)
    xs = _radix_pass(xs, 8)
    xs = _radix_pass(xs, 16)
    xs = _radix_pass(xs, 24)
    return xs


def radix_sort_u64(xs) -> list:
    """LSD byte radix sort for 64-bit unsigned ints."""
    xs = list(xs)
    for shift in range(0, 64, 8):
        xs = _radix_pass(xs, shift)
    return xs


def radix_sort_i32(xs) -> list:
    """Signed 32-bit: flip the sign bit before/after unsigned radix."""
    flip = 0x80000000
    flipped = [((v ^ flip) & MASK32) for v in xs]
    flipped = radix_sort_u32(flipped)
    out: list = []
    for v in flipped:
        v = (v ^ flip) & MASK32
        # restore sign-extended negative
        if (v & flip) != 0:
            v = v - (1 << 32)
        out = out + [v]
    return out


def _str_char_at(s: str, i: int) -> int:
    if i >= len(s):
        return -1
    return list(s[i].encode("utf-8"))[0]


def _msd_sort(xs, depth: int) -> list:
    if len(xs) <= 1:
        return list(xs)
    # buckets[0] for "end of string", [1..256] for each byte value
    buckets: list = [[] for _ in range(257)]
    for s in xs:
        buckets[_str_char_at(s, depth) + 1] = (
            buckets[_str_char_at(s, depth) + 1] + [s]
        )
    out = list(buckets[0])  # strings whose length == depth
    for b in range(1, 257):
        out = out + _msd_sort(buckets[b], depth + 1)
    return out


def radix_sort_str(xs) -> list:
    """MSD radix sort for a list of strings. Stable for equal keys."""
    return _msd_sort(list(xs), 0)
