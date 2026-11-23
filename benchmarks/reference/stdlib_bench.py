#!/usr/bin/env python3
"""Stdlib micro-benchmark reference implementations (Python).

Five workloads, identical inputs to the Node and Lateralus versions:

  1. xxhash64        — XXH64 over 2 MB
  2. lz4             — compress + decompress round-trip of 4 MB
  3. chacha20        — 1 MB keystream (RFC 8439)
  4. aho_corasick    — 1,000 patterns scanned over 1 MB of text
  5. radix_sort_u32  — sort 100,000 u32 keys

Each benchmark prints exactly one line, `<name> <output>`, where `<output>` is a
deterministic digest of the result so cross-language runs can be diffed
byte-for-byte.

Usage:
    python3 stdlib_bench.py <name>
    python3 stdlib_bench.py all
"""

from __future__ import annotations

import sys

M32 = 0xFFFFFFFF
M64 = 0xFFFFFFFFFFFFFFFF

# ── deterministic input generators (must match bench.js exactly) ─────────────
class XorShift32:
    __slots__ = ("s",)

    def __init__(self, seed: int) -> None:
        self.s = seed & M32 or 0x9E3779B9

    def next(self) -> int:
        x = self.s
        x ^= (x << 13) & M32
        x ^= x >> 17
        x ^= (x << 5) & M32
        self.s = x & M32
        return self.s


def _rfc8439_selftest() -> None:
    """RFC 8439 §2.4.2 test vector for the block function."""
    key = bytes(range(32))
    nonce = bytes([0, 0, 0, 9, 0, 0, 0, 0x4A, 0, 0, 0, 0])
    blk = chacha20_block(key, 1, nonce)
    want = bytes.fromhex("10f1e7e4d13b5915500fdd1fa32071c4")
    if blk[:16] != want:
        raise SystemExit(f"chacha20 block != RFC 8439 vector: {blk[:16].hex()}")


def gen_bytes(n: int, seed: int) -> bytes:
    rng = XorShift32(seed)
    out = bytearray(n)
    for i in range(0, n, 4):
        w = rng.next()
        chunk = w.to_bytes(4, "little")
        out[i:i + 4] = chunk[: min(4, n - i)]
    return bytes(out)


def gen_u32(n: int, seed: int) -> list[int]:
    rng = XorShift32(seed)
    return [rng.next() for _ in range(n)]


def gen_text(n: int, seed: int) -> bytes:
    """Printable ASCII — keeps the AC scan realistic and language-neutral."""
    rng = XorShift32(seed)
    out = bytearray(n)
    for i in range(n):
        out[i] = 32 + (rng.next() % 95)
    return bytes(out)


def gen_patterns(count: int, seed: int, text: bytes) -> list[bytes]:
    """Deterministic 4–12 byte patterns, most of them actually present."""
    rng = XorShift32(seed)
    pats: list[bytes] = []
    for i in range(count):
        if i % 4 != 0 and len(text) > 16:
            ln = 4 + (rng.next() % 9)
            start = rng.next() % (len(text) - ln)
            pats.append(text[start:start + ln])
        else:
            ln = 4 + (rng.next() % 9)
            pats.append(bytes(32 + (rng.next() % 95) for _ in range(ln)))
    return pats


# ── 1. xxHash64 ─────────────────────────────────────────────────────────────
P1 = 0x9E3779B185EBCA87
P2 = 0xC2B2AE3D27D4EB4F
P3 = 0x165667B19E3779F9
P4 = 0x85EBCA77C2B2AE63
P5 = 0x27D4EB2F165667C5


def _rotl64(x: int, r: int) -> int:
    return ((x << r) | (x >> (64 - r))) & M64


def _round64(acc: int, lane: int) -> int:
    acc = (acc + lane * P2) & M64
    acc = _rotl64(acc, 31)
    return (acc * P1) & M64


def _merge64(acc: int, val: int) -> int:
    acc ^= _round64(0, val)
    return (acc * P1 + P4) & M64


def xxh64(data: bytes, seed: int = 0) -> int:
    n = len(data)
    i = 0
    if n >= 32:
        v1 = (seed + P1 + P2) & M64
        v2 = (seed + P2) & M64
        v3 = seed & M64
        v4 = (seed - P1) & M64
        while i + 32 <= n:
            v1 = _round64(v1, int.from_bytes(data[i:i + 8], "little"))
            v2 = _round64(v2, int.from_bytes(data[i + 8:i + 16], "little"))
            v3 = _round64(v3, int.from_bytes(data[i + 16:i + 24], "little"))
            v4 = _round64(v4, int.from_bytes(data[i + 24:i + 32], "little"))
            i += 32
        h = (_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18)) & M64
        h = _merge64(h, v1)
        h = _merge64(h, v2)
        h = _merge64(h, v3)
        h = _merge64(h, v4)
    else:
        h = (seed + P5) & M64
    h = (h + n) & M64
    while i + 8 <= n:
        h ^= _round64(0, int.from_bytes(data[i:i + 8], "little"))
        h = (_rotl64(h, 27) * P1 + P4) & M64
        i += 8
    if i + 4 <= n:
        h ^= (int.from_bytes(data[i:i + 4], "little") * P1) & M64
        h = (_rotl64(h, 23) * P2 + P3) & M64
        i += 4
    while i < n:
        h ^= (data[i] * P5) & M64
        h = (_rotl64(h, 11) * P1) & M64
        i += 1
    h ^= h >> 33
    h = (h * P2) & M64
    h ^= h >> 29
    h = (h * P3) & M64
    h ^= h >> 32
    return h


# ── 2. LZ4 block (deterministic greedy matcher) ─────────────────────────────
MIN_MATCH = 4
HASH_BITS = 12          # 4096 buckets — small on purpose, honest LZ4 numbers
MAX_OFFSET = 65535


def lz4_compress(src: bytes) -> bytes:
    n = len(src)
    out = bytearray()
    table: dict[int, int] = {}
    anchor = 0
    i = 0
    while i + MIN_MATCH <= n:
        word = int.from_bytes(src[i:i + 4], "little")
        key = ((word * 2654435761) & M32) >> (32 - HASH_BITS)
        cand = table.get(key, -1)
        table[key] = i
        if cand >= 0 and i - cand <= MAX_OFFSET and src[cand:cand + MIN_MATCH] == src[i:i + MIN_MATCH]:
            ml = MIN_MATCH
            while i + ml < n and cand + ml < i and src[cand + ml] == src[i + ml]:
                ml += 1
            lit = i - anchor
            token_lit = min(lit, 15)
            token_ml = ml - MIN_MATCH
            out.append((token_lit << 4) | min(token_ml, 15))
            if lit >= 15:
                rem = lit - 15
                while rem >= 255:
                    out.append(255)
                    rem -= 255
                out.append(rem)
            out += src[anchor:i]
            off = i - cand
            out.append(off & 0xFF)
            out.append((off >> 8) & 0xFF)
            if token_ml >= 15:
                rem = token_ml - 15
                while rem >= 255:
                    out.append(255)
                    rem -= 255
                out.append(rem)
            i += ml
            anchor = i
        else:
            i += 1
    # trailing literals
    lit = n - anchor
    token_lit = min(lit, 15)
    out.append(token_lit << 4)
    if lit >= 15:
        rem = lit - 15
        while rem >= 255:
            out.append(255)
            rem -= 255
        out.append(rem)
    out += src[anchor:]
    return bytes(out)


def lz4_decompress(src: bytes, out_len: int) -> bytes:
    out = bytearray()
    i = 0
    n = len(src)
    while i < n and len(out) < out_len:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        out += src[i:i + lit]
        i += lit
        if i >= n or len(out) >= out_len:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0:
            raise ValueError("bad offset")
        ml = token & 0x0F
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += MIN_MATCH
        start = len(out) - off
        for k in range(ml):
            out.append(out[start + k])
    if len(out) != out_len:
        raise ValueError(f"length mismatch {len(out)} != {out_len}")
    return bytes(out)


# ── 3. ChaCha20 (RFC 8439) ──────────────────────────────────────────────────
def _rotl32(v: int, c: int) -> int:
    return ((v << c) & M32) | (v >> (32 - c))


def _quarter(s: list[int], a: int, b: int, c: int, d: int) -> None:
    s[a] = (s[a] + s[b]) & M32
    s[d] = _rotl32(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & M32
    s[b] = _rotl32(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & M32
    s[d] = _rotl32(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & M32
    s[b] = _rotl32(s[b] ^ s[c], 7)


def chacha20_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    c = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
    c += [int.from_bytes(key[i:i + 4], "little") for i in range(0, 32, 4)]
    c += [counter & M32]
    c += [int.from_bytes(nonce[i:i + 4], "little") for i in range(0, 12, 4)]
    w = c[:]
    for _ in range(10):
        _quarter(w, 0, 4, 8, 12)
        _quarter(w, 1, 5, 9, 13)
        _quarter(w, 2, 6, 10, 14)
        _quarter(w, 3, 7, 11, 15)
        _quarter(w, 0, 5, 10, 15)
        _quarter(w, 1, 6, 11, 12)
        _quarter(w, 2, 7, 8, 13)
        _quarter(w, 3, 4, 9, 14)
    out = bytearray(64)
    for i in range(16):
        out[i * 4:i * 4 + 4] = ((w[i] + c[i]) & M32).to_bytes(4, "little")
    return bytes(out)


def chacha20_keystream(n: int, key: bytes, nonce: bytes) -> bytes:
    out = bytearray()
    ctr = 1
    while len(out) < n:
        out += chacha20_block(key, ctr, nonce)
        ctr += 1
    return bytes(out[:n])


# ── 4. Aho–Corasick ─────────────────────────────────────────────────────────
def ac_build(patterns: list[bytes]) -> tuple[list[dict[int, int]], list[int], list[int]]:
    goto: list[dict[int, int]] = [{}]
    fail = [0]
    out_count = [0]
    for p in patterns:
        cur = 0
        for ch in p:
            nxt = goto[cur].get(ch)
            if nxt is None:
                goto.append({})
                fail.append(0)
                out_count.append(0)
                nxt = len(goto) - 1
                goto[cur][ch] = nxt
            cur = nxt
        out_count[cur] += 1
    q: list[int] = []
    for ch, s in goto[0].items():
        fail[s] = 0
        q.append(s)
    head = 0
    while head < len(q):
        r = q[head]
        head += 1
        for ch, s in goto[r].items():
            q.append(s)
            f = fail[r]
            while f and ch not in goto[f]:
                f = fail[f]
            fail[s] = goto[f].get(ch, 0) if f or ch in goto[0] else 0
            if fail[s] == s:
                fail[s] = 0
            out_count[s] += out_count[fail[s]]
    return goto, fail, out_count


def ac_scan(text: bytes, patterns: list[bytes]) -> int:
    goto, fail, cnt = ac_build(patterns)
    state = 0
    total = 0
    for ch in text:
        while state and ch not in goto[state]:
            state = fail[state]
        state = goto[state].get(ch, 0)
        total += cnt[state]
    return total


# ── 5. radix sort u32 ───────────────────────────────────────────────────────
def radix_sort_u32(a: list[int]) -> list[int]:
    src = list(a)
    dst = [0] * len(src)
    for shift in (0, 8, 16, 24):
        cnt = [0] * 256
        for v in src:
            cnt[(v >> shift) & 0xFF] += 1
        total = 0
        for i in range(256):
            c = cnt[i]
            cnt[i] = total
            total += c
        for v in src:
            b = (v >> shift) & 0xFF
            dst[cnt[b]] = v
            cnt[b] += 1
        src, dst = dst, src
    return src


# ── checksum used in every output line ──────────────────────────────────────
def adler32(data: bytes) -> int:
    a, b = 1, 0
    for byte in data:
        a = (a + byte) % 65521
        b = (b + a) % 65521
    return ((b << 16) | a) & M32


# ── workloads ───────────────────────────────────────────────────────────────
def bench_xxhash() -> str:
    data = gen_bytes(2 * 1024 * 1024, 0x12345678)
    return f"{xxh64(data):016x}"


def bench_lz4() -> str:
    data = gen_bytes(4 * 1024 * 1024, 0x2468ACE0)
    packed = lz4_compress(data)
    back = lz4_decompress(packed, len(data))
    if back != data:
        raise SystemExit("lz4 round-trip mismatch")
    return f"ok:{len(data)}:{adler32(packed):08x}:{len(packed)}"


def bench_chacha20() -> str:
    data = gen_bytes(1024 * 1024, 0x0BADF00D)
    key = bytes(range(32))
    nonce = bytes(range(12))
    ks = chacha20_keystream(len(data), key, nonce)
    ct = bytes(x ^ y for x, y in zip(data, ks))
    return f"{ct[:8].hex()}:{adler32(ct):08x}"


def bench_aho() -> str:
    text = gen_text(1024 * 1024, 0x5EED1234)
    pats = gen_patterns(1000, 0xC0FFEE11, text)
    return f"{ac_scan(text, pats)}"


def bench_radix() -> str:
    keys = gen_u32(100_000, 0xDEADBEEF)
    s = radix_sort_u32(keys)
    if s != sorted(keys):
        raise SystemExit("radix sort mismatch vs python sorted()")
    raw = b"".join(v.to_bytes(4, "little") for v in s)
    return f"{s[0]:08x}:{s[-1]:08x}:{adler32(raw):08x}"


BENCHES = {
    "xxhash": bench_xxhash,
    "lz4": bench_lz4,
    "chacha20": bench_chacha20,
    "aho_corasick": bench_aho,
    "radix_sort_u32": bench_radix,
}


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    _rfc8439_selftest()
    if which == "all":
        for name, fn in BENCHES.items():
            print(f"{name} {fn()}")
    elif which in BENCHES:
        print(f"{which} {BENCHES[which]()}")
    else:
        print(f"unknown benchmark {which!r}; choose from {', '.join(BENCHES)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())