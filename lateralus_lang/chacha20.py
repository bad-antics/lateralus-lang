"""
LATERALUS Standard Library — chacha20
Python implementation of stdlib/chacha20.ltl

Bit-for-bit mirror of the Lateralus ChaCha20 stream cipher (RFC 8439).
Used as the runtime backing for `import chacha20` in transpiled
Lateralus code (see codegen/python.py alias map).

Output is accumulated in a bytearray (O(1) amortised append) instead
of the `out = out + [b]` pattern in the .ltl source, which is O(n)
per byte and makes multi-MB inputs quadratic. The ciphertext bytes
are identical to the .ltl implementation.
"""
from __future__ import annotations

MASK32 = 0xFFFFFFFF


def _u32(x: int) -> int:
    return x & MASK32


def _rotl32(v: int, r: int) -> int:
    v &= MASK32
    return ((v << r) | (v >> (32 - r))) & MASK32


def _read_u32_le(buf, i: int) -> int:
    return buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)


def _u32_to_le(v: int) -> list:
    return [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]


def _quarter_round(s: list, a: int, b: int, c: int, d: int) -> list:
    s[a] = _u32(s[a] + s[b])
    s[d] = _rotl32(s[d] ^ s[a], 16)
    s[c] = _u32(s[c] + s[d])
    s[b] = _rotl32(s[b] ^ s[c], 12)
    s[a] = _u32(s[a] + s[b])
    s[d] = _rotl32(s[d] ^ s[a], 8)
    s[c] = _u32(s[c] + s[d])
    s[b] = _rotl32(s[b] ^ s[c], 7)
    return s


def block(key, nonce, counter: int) -> list:
    """Build the 64-byte keystream block at the given counter."""
    s = [
        0x61707865,
        0x3320646E,
        0x79622D32,
        0x6B206574,
        _read_u32_le(key, 0),
        _read_u32_le(key, 4),
        _read_u32_le(key, 8),
        _read_u32_le(key, 12),
        _read_u32_le(key, 16),
        _read_u32_le(key, 20),
        _read_u32_le(key, 24),
        _read_u32_le(key, 28),
        counter & MASK32,
        _read_u32_le(nonce, 0),
        _read_u32_le(nonce, 4),
        _read_u32_le(nonce, 8),
    ]
    working = list(s)
    for _ in range(10):
        # column rounds
        _quarter_round(working, 0, 4, 8, 12)
        _quarter_round(working, 1, 5, 9, 13)
        _quarter_round(working, 2, 6, 10, 14)
        _quarter_round(working, 3, 7, 11, 15)
        # diagonal rounds
        _quarter_round(working, 0, 5, 10, 15)
        _quarter_round(working, 1, 6, 11, 12)
        _quarter_round(working, 2, 7, 8, 13)
        _quarter_round(working, 3, 4, 9, 14)
    out: list = []
    for k in range(16):
        out = out + _u32_to_le(_u32(working[k] + s[k]))
    return out


def xor(key, nonce, initial_counter: int, data) -> list:
    """Encrypt or decrypt (same op, XOR is its own inverse)."""
    data = bytes(data)
    out = bytearray()
    n = len(data)
    i = 0
    counter = initial_counter
    while i < n:
        ks = block(key, nonce, counter)
        take = 64 if n - i >= 64 else n - i
        out.extend(b ^ k for b, k in zip(data[i : i + take], ks))
        i = i + 64
        counter = counter + 1
    return list(out)
