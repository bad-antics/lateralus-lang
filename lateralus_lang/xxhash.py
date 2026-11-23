"""
LATERALUS Standard Library — xxhash
Python implementation of stdlib/xxhash.ltl

Bit-for-bit mirror of the Lateralus XXH64 implementation (canonical
Cyan4973/xxHash spec). Used as the runtime backing for `import xxhash`
in transpiled Lateralus code (see codegen/python.py alias map).
"""
from __future__ import annotations

MASK = 0xFFFFFFFFFFFFFFFF
P1 = 0x9E3779B185EBCA87
P2 = 0xC2B2AE3D27D4EB4F
P3 = 0x165667B19E3779F9
P4 = 0x85EBCA77C2B2AE63
P5 = 0x27D4EB2F165667C5


def _u64(x: int) -> int:
    return x & MASK


def _rotl64(v: int, r: int) -> int:
    v &= MASK
    return ((v << r) | (v >> (64 - r))) & MASK


def _read_u64_le(buf, i: int) -> int:
    return (
        buf[i]
        | (buf[i + 1] << 8)
        | (buf[i + 2] << 16)
        | (buf[i + 3] << 24)
        | (buf[i + 4] << 32)
        | (buf[i + 5] << 40)
        | (buf[i + 6] << 48)
        | (buf[i + 7] << 56)
    )


def _read_u32_le(buf, i: int) -> int:
    return buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)


def _round64(acc: int, inp: int) -> int:
    acc = _u64(acc + _u64(inp * P2))
    acc = _rotl64(acc, 31)
    return _u64(acc * P1)


def _merge_round(acc: int, val: int) -> int:
    val = _round64(0, val)
    acc ^= val
    return _u64(_u64(acc * P1) + P4)


def hash64(buf, seed: int) -> int:
    """Hash a raw byte list with optional 64-bit seed."""
    n = len(buf)
    h = 0
    i = 0
    if n >= 32:
        v1 = _u64(seed + P1 + P2)
        v2 = _u64(seed + P2)
        v3 = _u64(seed + 0)
        v4 = _u64(seed - P1)
        while i + 32 <= n:
            v1 = _round64(v1, _read_u64_le(buf, i))
            v2 = _round64(v2, _read_u64_le(buf, i + 8))
            v3 = _round64(v3, _read_u64_le(buf, i + 16))
            v4 = _round64(v4, _read_u64_le(buf, i + 24))
            i += 32
        h = _u64(_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18))
        h = _merge_round(h, v1)
        h = _merge_round(h, v2)
        h = _merge_round(h, v3)
        h = _merge_round(h, v4)
    else:
        h = _u64(seed + P5)
    h = _u64(h + n)
    while i + 8 <= n:
        k1 = _round64(0, _read_u64_le(buf, i))
        h = _rotl64(h ^ k1, 27)
        h = _u64(_u64(h * P1) + P4)
        i += 8
    if i + 4 <= n:
        h = _u64(h ^ _u64(_read_u32_le(buf, i) * P1))
        h = _rotl64(h, 23)
        h = _u64(_u64(h * P2) + P3)
        i += 4
    while i < n:
        h = _u64(h ^ _u64(buf[i] * P5))
        h = _u64(_rotl64(h, 11) * P1)
        i += 1
    h ^= h >> 33
    h = _u64(h * P2)
    h ^= h >> 29
    h = _u64(h * P3)
    h ^= h >> 32
    return h


def hash64_str(s: str, seed: int) -> int:
    return hash64(list(s.encode("utf-8")), seed)


def fnv1a_64(buf) -> int:
    h = 0xCBF29CE484222325
    prime = 0x100000001B3
    for b in buf:
        h = (h ^ b) & MASK
        h = _u64(h * prime)
    return h


def fnv1a_64_str(s: str) -> int:
    return fnv1a_64(list(s.encode("utf-8")))
