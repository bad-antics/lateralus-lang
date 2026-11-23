#!/usr/bin/env python3
"""stdlib_bench.py — CPython reference for the Lateralus stdlib micro-benchmarks.

Five real-workload benchmarks that exercise the pure-Lateralus stdlib modules
(``stdlib/xxhash.ltl``, ``stdlib/lz4.ltl``, ``std/crypto/chacha20.ltl``,
``stdlib/aho_corasick.ltl``, ``stdlib/radix_sort.ltl``):

    #  workload                              size
    1  xxhash64                              2 MB
    2  lz4 compress + decompress round-trip  4 MB
    3  chacha20 keystream / encrypt          1 MB
    4  aho_corasick, 1,000 patterns          1 MB text
    5  radix_sort_u32                          100,000 keys

The Node port (``stdlib_bench.js``) is a line-for-line translation: identical
XorShift32 input generators (same seeds), identical algorithms, identical
digest lines.  ``diff <(python3 stdlib_bench.py) <(node stdlib_bench.js)`` is
empty.

Correctness is pinned to *published* vectors, not just cross-language
agreement — the startup self-check asserts:

    xxh64("")   == 0xef46db3751d8e999
    xxh64("abc")== 0x44bc2cf5ad770999
    xxh64("Nobody inspects the spammish repetition") == 0xfbcea83c8a378bf1
    adler32("Wikipedia") == 0x11e60398
    ChaCha20 block (RFC 8439 §2.4.2) keystream prefix == 224f51f3...

Each workload prints exactly one digest line so the harness can diff the
Python / Node / Lateralus outputs for equality.

MIT licensed.  Original work.
"""
from __future__ import annotations

import sys
import time

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF


# ── deterministic input generation (XorShift32, identical in .js / .ltl) ────
class XorShift32:
    __slots__ = ("s",)

    def __init__(self, seed: int) -> None:
        self.s = seed & MASK32

    def next_u32(self) -> int:
        x = self.s & MASK32
        x ^= (x << 13) & MASK32
        x ^= x >> 17
        x ^= (x << 5) & MASK32
        self.s = x & MASK32
        return self.s

    def next_byte(self) -> int:
        return self.next_u32() & 0xFF

    def bytes(self, n: int) -> bytearray:
        out = bytearray(n)
        i = 0
        while i < n:
            out[i] = self.next_byte()
            i += 1
        return out


# ── 1. xxHash64 (canonical Cyan4973 XXH64, single-shot) ─────────────────────
_P1 = 0x9E3779B185EBCA87
_P2 = 0xC2B2AE3D27D4EB4F
_P3 = 0x165667B19E3779F9
_P4 = 0x85EBCA77C2B2AE63
_P5 = 0x27D4EB2F165667C5


def _u64(x: int) -> int:
    return x & MASK64


def _rotl64(v: int, r: int) -> int:
    v &= MASK64
    return ((v << r) | (v >> (64 - r))) & MASK64


def _round64(acc: int, inp: int) -> int:
    acc = _u64(acc + _u64(inp * _P2))
    acc = _rotl64(acc, 31)
    return _u64(acc * _P1)


def _merge_round(acc: int, val: int) -> int:
    val = _round64(0, val)
    acc ^= val
    return _u64(_u64(acc * _P1) + _P4)


def xxh64(buf, seed: int = 0) -> int:
    n = len(buf)
    i = 0
    if n >= 32:
        v1 = _u64(seed + _P1 + _P2)
        v2 = _u64(seed + _P2)
        v3 = _u64(seed + 0)
        v4 = _u64(seed - _P1)
        while i + 32 <= n:
            v1 = _round64(v1, int.from_bytes(buf[i:i + 8], "little"))
            v2 = _round64(v2, int.from_bytes(buf[i + 8:i + 16], "little"))
            v3 = _round64(v3, int.from_bytes(buf[i + 16:i + 24], "little"))
            v4 = _round64(v4, int.from_bytes(buf[i + 24:i + 32], "little"))
            i += 32
        h = _u64(_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18))
        h = _merge_round(h, v1)
        h = _merge_round(h, v2)
        h = _merge_round(h, v3)
        h = _merge_round(h, v4)
    else:
        h = _u64(seed + _P5)
    h = _u64(h + n)
    while i + 8 <= n:
        k1 = _round64(0, int.from_bytes(buf[i:i + 8], "little"))
        h = _rotl64(h ^ k1, 27)
        h = _u64(_u64(h * _P1) + _P4)
        i += 8
    if i + 4 <= n:
        h = _u64(h ^ _u64(int.from_bytes(buf[i:i + 4], "little") * _P1))
        h = _rotl64(h, 23)
        h = _u64(_u64(h * _P2) + _P3)
        i += 4
    while i < n:
        h = _u64(h ^ _u64(buf[i] * _P5))
        h = _u64(_rotl64(h, 11) * _P1)
        i += 1
    h ^= h >> 33
    h = _u64(h * _P2)
    h ^= h >> 29
    h = _u64(h * _P3)
    h ^= h >> 32
    return h


def adler32(buf) -> int:
    a = 1
    b = 0
    for byte in buf:
        a = (a + byte) % 65521
        b = (b + a) % 65521
    return (b << 16) | a


# ── 2. LZ4 block format (greedy hash-chain matcher, "fast" mode) ────────────
_LZ4_MINMATCH = 4
_LZ4_HASH_BITS = 12
_LZ4_HASH_SIZE = 1 << _LZ4_HASH_BITS
_LZ4_HASH_MASK = _LZ4_HASH_SIZE - 1
_LZ4_MF_LIMIT = 12
_LZ4_LAST_LITS = 5
_LZ4_MAXD = 65535


def _lz4_hash4(buf, i: int) -> int:
    v = buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)
    # Knuth multiplicative hash; wrap to 32 bits BEFORE the shift so the
    # bucket index matches the JS / Lateralus crawler exactly.
    v &= MASK32
    return ((v * 2654435761) & MASK32) >> (32 - _LZ4_HASH_BITS) & _LZ4_HASH_MASK


def lz4_compress(src) -> bytearray:
    n = len(src)
    out = bytearray()
    anchor = 0
    i = 0
    if n < _LZ4_MF_LIMIT + _LZ4_LAST_LITS:
        lit_len = n
        if lit_len >= 15:
            out.append(0xF0)
            v = lit_len - 15
            while v >= 255:
                out.append(255)
                v -= 255
            out.append(v)
        else:
            out.append((lit_len << 4) & 0xFF)
        out += src[:n]
        return out

    htab = [-1] * _LZ4_HASH_SIZE
    end_limit = n - _LZ4_MF_LIMIT - _LZ4_LAST_LITS
    while i <= end_limit:
        hv = _lz4_hash4(src, i)
        ref_pos = htab[hv]
        htab[hv] = i
        if (ref_pos >= 0 and i - ref_pos <= _LZ4_MAXD
                and src[ref_pos] == src[i] and src[ref_pos + 1] == src[i + 1]
                and src[ref_pos + 2] == src[i + 2] and src[ref_pos + 3] == src[i + 3]):
            mlen = 4
            while i + mlen < n - _LZ4_LAST_LITS and src[ref_pos + mlen] == src[i + mlen]:
                mlen += 1
            lit_len = i - anchor
            mlen_t = mlen - _LZ4_MINMATCH
            t_lit = 15 if lit_len > 15 else lit_len
            t_m = 15 if mlen_t > 15 else mlen_t
            out.append(((t_lit << 4) | t_m) & 0xFF)
            if lit_len >= 15:
                v = lit_len - 15
                while v >= 255:
                    out.append(255)
                    v -= 255
                out.append(v)
            out += src[anchor:anchor + lit_len]
            off = i - ref_pos
            out.append(off & 0xFF)
            out.append((off >> 8) & 0xFF)
            if mlen_t >= 15:
                v = mlen_t - 15
                while v >= 255:
                    out.append(255)
                    v -= 255
                out.append(v)
            i += mlen
            anchor = i
        else:
            i += 1

    lit_len = n - anchor
    if lit_len >= 15:
        out.append(0xF0)
        v = lit_len - 15
        while v >= 255:
            out.append(255)
            v -= 255
        out.append(v)
    else:
        out.append((lit_len << 4) & 0xFF)
    out += src[anchor:anchor + lit_len]
    return out


def lz4_decompress(src) -> bytearray:
    n = len(src)
    out = bytearray()
    i = 0
    while i < n:
        tok = src[i]
        i += 1
        lit_len = (tok >> 4) & 0x0F
        if lit_len == 15:
            while True:
                b = src[i]
                i += 1
                lit_len += b
                if b != 255:
                    break
        out += src[i:i + lit_len]
        i += lit_len
        if i >= n:
            return out
        off = src[i] | (src[i + 1] << 8)
        i += 2
        mlen = tok & 0x0F
        if mlen == 15:
            while True:
                b = src[i]
                i += 1
                mlen += b
                if b != 255:
                    break
        mlen += _LZ4_MINMATCH
        start = len(out) - off
        m = 0
        while m < mlen:
            out.append(out[start + m])
            m += 1
    return out


# ── 3. ChaCha20 (RFC 8439) ──────────────────────────────────────────────────
def _rotl32(v: int, n: int) -> int:
    v &= MASK32
    return ((v << n) | (v >> (32 - n))) & MASK32


def _quarter_round(s, a, b, c, d) -> None:
    s[a] = (s[a] + s[b]) & MASK32
    s[d] = _rotl32(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & MASK32
    s[b] = _rotl32(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & MASK32
    s[d] = _rotl32(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & MASK32
    s[b] = _rotl32(s[b] ^ s[c], 7)


def chacha20_block(key, counter: int, nonce) -> bytes:
    constants = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
    state = constants[:]
    for i in range(8):
        state.append(int.from_bytes(key[i * 4:i * 4 + 4], "little"))
    state.append(counter & MASK32)            # word 12
    for i in range(3):                         # words 13,14,15 = nonce
        state.append(int.from_bytes(nonce[i * 4:i * 4 + 4], "little"))
    working = state[:]
    for _ in range(10):
        _quarter_round(working, 0, 4, 8, 12)
        _quarter_round(working, 1, 5, 9, 13)
        _quarter_round(working, 2, 6, 10, 14)
        _quarter_round(working, 3, 7, 11, 15)
        _quarter_round(working, 0, 5, 10, 15)
        _quarter_round(working, 1, 6, 11, 12)
        _quarter_round(working, 2, 7, 8, 13)
        _quarter_round(working, 3, 4, 9, 14)
    out = bytearray(64)
    for i in range(16):
        v = (working[i] + state[i]) & MASK32
        out[i * 4:i * 4 + 4] = v.to_bytes(4, "little")
    return bytes(out)


def chacha20_encrypt(key, nonce, data) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    n = len(data)
    while offset < n:
        ks = chacha20_block(key, counter, nonce)
        counter = (counter + 1) & MASK32
        block_len = min(64, n - offset)
        for i in range(block_len):
            out[offset + i] = data[offset + i] ^ ks[i]
        offset += block_len
    return bytes(out)


# ── 4. Aho-Corasick multi-pattern search ────────────────────────────────────
def ac_build(patterns):
    goto = [{}]
    fail = [0]
    output = [[]]
    for pi, p in enumerate(patterns):
        node = 0
        for ch in p:
            c = ord(ch)
            if c in goto[node]:
                node = goto[node][c]
            else:
                goto.append({})
                fail.append(0)
                output.append([])
                new_id = len(goto) - 1
                goto[node][c] = new_id
                node = new_id
        output[node].append(pi)
    # BFS fail pointers
    queue = []
    for c, child in goto[0].items():
        fail[child] = 0
        queue.append(child)
    head = 0
    while head < len(queue):
        u = queue[head]
        head += 1
        for c, v in goto[u].items():
            queue.append(v)
            f = fail[u]
            while f > 0 and c not in goto[f]:
                f = fail[f]
            fallback = goto[f].get(c, 0)
            if fallback == v:
                fallback = 0
            fail[v] = fallback
            output[v] = output[v] + output[fallback]
    return goto, fail, output


def ac_find_all(auto, text):
    goto, fail, output = auto
    hits = []
    node = 0
    for i, ch in enumerate(text):
        c = ord(ch)
        while node > 0 and c not in goto[node]:
            node = fail[node]
        if c in goto[node]:
            node = goto[node][c]
        for pid in output[node]:
            hits.append((pid, i + 1))
    return hits


# ── 5. radix_sort_u32 (LSD byte radix, 4 passes) ────────────────────────────
def radix_sort_u32(xs):
    out = list(xs)
    for shift in (0, 8, 16, 24):
        counts = [0] * 256
        for v in out:
            counts[(v >> shift) & 0xFF] += 1
        # prefix sums -> starting offsets
        total = 0
        for b in range(256):
            c = counts[b]
            counts[b] = total
            total += c
        tmp = [0] * len(out)
        for v in out:
            b = (v >> shift) & 0xFF
            tmp[counts[b]] = v
            counts[b] += 1
        out = tmp
    return out


# ── correctness self-check (published vectors) ──────────────────────────────
def self_check() -> None:
    assert xxh64(b"") == 0xEF46DB3751D8E999, hex(xxh64(b""))
    assert xxh64(b"abc") == 0x44BC2CF5AD770999, hex(xxh64(b"abc"))
    assert xxh64(b"Nobody inspects the spammish repetition") == 0xFBCEA83C8A378BF1
    assert adler32(b"Wikipedia") == 0x11E60398, hex(adler32(b"Wikipedia"))
    # RFC 8439 §2.4.2 ChaCha20 block: key 00..1f, nonce 000000000000004a00000000,
    # counter 1 -> first 16 keystream bytes 224f51f3401bd9e12fde276fb8631ded.
    key = bytes(range(32))
    nonce = bytes.fromhex("000000000000004a00000000")
    ks = chacha20_block(key, 1, nonce)
    assert ks[:16].hex() == "224f51f3401bd9e12fde276fb8631ded", ks[:16].hex()


# ── driver ──────────────────────────────────────────────────────────────────
# Two size profiles.  "full" is the headline benchmark (issue #865 table).
# "verify" is a reduced size at which the pure-Lateralus tree-walking
# interpreter can run in a few seconds while still producing digest lines
# that match CPython and Node.js *exactly* (same seeds, same algorithms).
PROFILES = {
    "full":   dict(xxhash=2 * 1024 * 1024, lz4=4 * 1024 * 1024,
                   chacha=1 * 1024 * 1024, ac_patterns=1000,
                   ac_text=1 * 1024 * 1024, radix=100000),
    "verify": dict(xxhash=512, lz4=2048, chacha=512,
                   ac_patterns=40, ac_text=2048, radix=2000),
}


def _hex64(v: int) -> str:
    return f"{v & MASK64:016x}"


def _hex32(v: int) -> str:
    return f"{v & MASK32:08x}"


def run(which: str | None = None, profile: str = "full") -> None:
    self_check()
    sz = PROFILES[profile]

    selected = which or "all"

    if selected in ("all", "xxhash"):
        data = XorShift32(0x1234ABCD).bytes(sz["xxhash"])
        h = xxh64(data, 0)
        print(f"xxhash {_hex64(h)}")

    if selected in ("all", "lz4"):
        src = XorShift32(0xFEEDFACE).bytes(sz["lz4"])
        packed = lz4_compress(src)
        back = lz4_decompress(packed)
        ok = "ok" if bytes(back) == bytes(src) else "BAD"
        print(f"lz4 {ok}:{len(src)}:{_hex32(adler32(back))}:{len(packed)}")

    if selected in ("all", "chacha20"):
        key = XorShift32(0x0BADF00D).bytes(32)
        nonce = XorShift32(0x00C0FFEE).bytes(12)
        data = XorShift32(0xDEADBEEF).bytes(sz["chacha"])
        ct = chacha20_encrypt(key, nonce, data)
        # two independent 64-bit hashes of the ciphertext
        h1 = xxh64(ct, 0)
        h2 = xxh64(ct, 1)
        print(f"chacha20 {_hex64(h1)}:{_hex32(h2)}")

    if selected in ("all", "aho_corasick"):
        rng = XorShift32(0x5EED1234)
        # patterns of length 4..8 over a 4-letter alphabet
        alphabet = "ACGT"
        patterns = []
        for _ in range(sz["ac_patterns"]):
            plen = 4 + (rng.next_u32() % 5)
            s = []
            for _ in range(plen):
                s.append(alphabet[rng.next_u32() % 4])
            patterns.append("".join(s))
        # text over the same alphabet
        text_chars = []
        total = sz["ac_text"]
        for _ in range(total):
            text_chars.append(alphabet[rng.next_u32() % 4])
        text = "".join(text_chars)
        auto = ac_build(patterns)
        hits = ac_find_all(auto, text)
        print(f"aho_corasick {len(hits)}")

    if selected in ("all", "radix_sort"):
        rng = XorShift32(0x0BADCAFE)
        keys = [rng.next_u32() for _ in range(sz["radix"])]
        srt = radix_sort_u32(keys)
        # checksums: first, last, and xor-fold of the sorted sequence
        first = srt[0] if srt else 0
        last = srt[-1] if srt else 0
        acc = 0
        for v in srt:
            acc ^= v
        print(f"radix_sort_u32 {_hex32(first)}:{_hex32(last)}:{_hex32(acc)}")


def main(argv: list[str]) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    profile = argv[2] if len(argv) > 2 else "full"
    t0 = time.perf_counter()
    run(which, profile)
    dt = time.perf_counter() - t0
    print(f"# python {sys.version.split()[0]} profile={profile} elapsed {dt:.3f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))