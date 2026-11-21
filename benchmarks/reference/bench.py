"""Python reference implementations matching benchmarks/src/*.ltl exactly."""
import math
import sys


def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def sieve(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = False
    is_prime[1] = False
    p = 2
    while p * p <= n:
        if is_prime[p]:
            j = p * p
            while j <= n:
                is_prime[j] = False
                j += p
        p += 1
    return sum(1 for x in is_prime if x)


def mandelbrot(width, height, max_iter):
    total = 0
    for y in range(height):
        for x in range(width):
            cx = -2.0 + (x / width) * 3.0
            cy = -1.5 + (y / height) * 3.0
            zx = 0.0
            zy = 0.0
            i = 0
            while i < max_iter:
                zx2 = zx * zx
                zy2 = zy * zy
                if zx2 + zy2 > 4.0:
                    break
                new_zx = zx2 - zy2 + cx
                zy = 2.0 * zx * zy + cy
                zx = new_zx
                i += 1
            total += i
    return total


def nbody(n_bodies, iterations):
    xs = [0.0, 4.84, 8.34, 12.89, 15.37]
    ys = [0.0, 1.16, 4.12, 11.73, 25.92]
    vxs = [0.0, 0.00166, 0.00277, 0.00296, 0.00268]
    vys = [0.0, 0.00769, 0.00499, 0.00237, 0.00150]
    ms = [39.47, 0.0377, 0.113, 0.0349, 0.0534]
    for _ in range(iterations):
        for i in range(n_bodies):
            for j in range(i + 1, n_bodies):
                dx = xs[i] - xs[j]
                dy = ys[i] - ys[j]
                d2 = dx * dx + dy * dy + 0.0001
                d = math.sqrt(d2)
                mag = 0.01 / (d2 * d)
                vxs[i] -= dx * ms[j] * mag
                vys[i] -= dy * ms[j] * mag
                vxs[j] += dx * ms[i] * mag
                vys[j] += dy * ms[i] * mag
        for k in range(n_bodies):
            xs[k] += 0.01 * vxs[k]
            ys[k] += 0.01 * vys[k]
    return sum(xs) + sum(ys)


class Tree:
    __slots__ = ("left", "right")

    def __init__(self, left, right):
        self.left = left
        self.right = right


def make_tree(depth):
    if depth == 0:
        return 0
    return Tree(make_tree(depth - 1), make_tree(depth - 1))


def check_tree(node):
    if node == 0:
        return 1
    return 1 + check_tree(node.left) + check_tree(node.right)


# ---------------------------------------------------------------------------
# stdlib micro-benchmark references (matching benchmarks/src/stdlib_*.ltl).
# Pure standard-library implementations -- no third-party packages required.
#   - xxhash64  : real XXH64 (byte-identical to the Lateralus stdlib hash64)
#   - lz4       : simple hash-chain LZ77 round-trip (not the LZ4 block format)
#   - chacha20  : RFC 8439 stream cipher (matches the Lateralus stdlib xor)
#   - aho_corasick : naive multi-pattern search (str.count per pattern)
#   - radix_sort: LSD byte radix sort over u32
# ---------------------------------------------------------------------------

MASK64 = (1 << 64) - 1

XXH_P1 = 0x9E3779B185EBCA87
XXH_P2 = 0xC2B2AE3D27D4EB4F
XXH_P3 = 0x165667B19E3779F9
XXH_P4 = 0x85EBCA77C2B2AE63
XXH_P5 = 0x27D4EB2F165667C5


def _rotl64(v, r):
    return ((v << r) | (v >> (64 - r))) & MASK64


def _xxh_round(acc, inp):
    acc = (acc + (inp * XXH_P2) & MASK64) & MASK64
    acc = _rotl64(acc, 31)
    return (acc * XXH_P1) & MASK64


def _xxh_merge(acc, val):
    val = _xxh_round(0, val)
    acc ^= val
    return (acc * XXH_P1 + XXH_P4) & MASK64


def xxh64(data, seed=0):
    """XXH64 of a bytes object. Byte-identical to the Lateralus stdlib."""
    n = len(data)
    h = 0
    i = 0
    if n >= 32:
        v1 = (seed + XXH_P1 + XXH_P2) & MASK64
        v2 = (seed + XXH_P2) & MASK64
        v3 = seed & MASK64
        v4 = (seed - XXH_P1) & MASK64
        while i + 32 <= n:
            v1 = _xxh_round(v1, int.from_bytes(data[i:i + 8], "little"))
            v2 = _xxh_round(v2, int.from_bytes(data[i + 8:i + 16], "little"))
            v3 = _xxh_round(v3, int.from_bytes(data[i + 16:i + 24], "little"))
            v4 = _xxh_round(v4, int.from_bytes(data[i + 24:i + 32], "little"))
            i += 32
        h = (_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18)) & MASK64
        h = _xxh_merge(h, v1)
        h = _xxh_merge(h, v2)
        h = _xxh_merge(h, v3)
        h = _xxh_merge(h, v4)
    else:
        h = (seed + XXH_P5) & MASK64
    h = (h + n) & MASK64
    while i + 8 <= n:
        k1 = _xxh_round(0, int.from_bytes(data[i:i + 8], "little"))
        h = _rotl64(h ^ k1, 27)
        h = (h * XXH_P1 + XXH_P4) & MASK64
        i += 8
    if i + 4 <= n:
        h = (h ^ ((int.from_bytes(data[i:i + 4], "little") * XXH_P1) & MASK64)) & MASK64
        h = _rotl64(h, 23)
        h = (h * XXH_P2 + XXH_P3) & MASK64
        i += 4
    while i < n:
        h = (h ^ ((data[i] * XXH_P5) & MASK64)) & MASK64
        h = _rotl64(h, 11) * XXH_P1 & MASK64
        i += 1
    h ^= h >> 33
    h = (h * XXH_P2) & MASK64
    h ^= h >> 29
    h = (h * XXH_P3) & MASK64
    h ^= h >> 32
    return h & MASK64


def checksum64(xs):
    """Position-weighted 64-bit checksum; identical across backends."""
    s = 0
    for i, v in enumerate(xs):
        s += v * (i + 1)
    return s & MASK64


# -- simple hash-chain LZ77 (round-trip; token format: 0=literal, 1=match) --

_LZ_MIN_MATCH = 4
_LZ_MAX_OFFSET = 65535
_LZ_MAX_MATCH = 65535


def _lz_key(data, i):
    return data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24)


def lz77_compress(data):
    n = len(data)
    out = bytearray()
    table = {}
    i = 0
    while i < n:
        off = -1
        mlen = 0
        if i + _LZ_MIN_MATCH <= n:
            j = table.get(_lz_key(data, i), -1)
            if j >= 0 and i - j <= _LZ_MAX_OFFSET:
                m = 0
                limit = min(_LZ_MAX_MATCH, n - i)
                while m < limit and data[j + m] == data[i + m]:
                    m += 1
                if m >= _LZ_MIN_MATCH:
                    off = i - j
                    mlen = m
        if off > 0:
            out.append(1)
            out.append(off & 0xFF)
            out.append((off >> 8) & 0xFF)
            out.append(mlen & 0xFF)
            out.append((mlen >> 8) & 0xFF)
            for k in range(1, mlen):
                if i + k + _LZ_MIN_MATCH <= n:
                    table[_lz_key(data, i + k)] = i + k
            i += mlen
        else:
            out.append(0)
            out.append(data[i])
            if i + _LZ_MIN_MATCH <= n:
                table[_lz_key(data, i)] = i
            i += 1
    return bytes(out)


def lz77_decompress(comp):
    out = bytearray()
    i = 0
    n = len(comp)
    while i < n:
        if comp[i] == 0:
            out.append(comp[i + 1])
            i += 2
        else:
            off = comp[i + 1] | (comp[i + 2] << 8)
            mlen = comp[i + 3] | (comp[i + 4] << 8)
            start = len(out) - off
            for _ in range(mlen):
                out.append(out[start])
                start += 1
            i += 5
    return bytes(out)


# -- pure-Python ChaCha20 (RFC 8439) --


def _rotl32(v, r):
    return ((v << r) | (v >> (32 - r))) & 0xFFFFFFFF


def _chacha_qr(s, a, b, c, d):
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF
    s[d] = _rotl32(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF
    s[b] = _rotl32(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF
    s[d] = _rotl32(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF
    s[b] = _rotl32(s[b] ^ s[c], 7)


def chacha20_block(key, counter, nonce):
    const = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
    s = (const
         + [int.from_bytes(key[i:i + 4], "little") for i in range(0, 32, 4)]
         + [counter & 0xFFFFFFFF]
         + [int.from_bytes(nonce[i:i + 4], "little") for i in range(0, 12, 4)])
    w = list(s)
    for _ in range(10):
        _chacha_qr(w, 0, 4, 8, 12)
        _chacha_qr(w, 1, 5, 9, 13)
        _chacha_qr(w, 2, 6, 10, 14)
        _chacha_qr(w, 3, 7, 11, 15)
        _chacha_qr(w, 0, 5, 10, 15)
        _chacha_qr(w, 1, 6, 11, 12)
        _chacha_qr(w, 2, 7, 8, 13)
        _chacha_qr(w, 3, 4, 9, 14)
    out = bytearray()
    for i in range(16):
        out += ((w[i] + s[i]) & 0xFFFFFFFF).to_bytes(4, "little")
    return bytes(out)


def chacha20_encrypt(key, nonce, counter, plaintext):
    out = bytearray()
    i = 0
    ctr = counter
    while i < len(plaintext):
        ks = chacha20_block(key, ctr, nonce)
        for j in range(min(64, len(plaintext) - i)):
            out.append(plaintext[i + j] ^ ks[j])
        i += 64
        ctr += 1
    return bytes(out)


def multi_pattern_count(text, patterns):
    return sum(text.count(p) for p in patterns)


def radix_sort_u32(xs):
    for shift in (0, 8, 16, 24):
        buckets = [[] for _ in range(256)]
        for v in xs:
            buckets[(v >> shift) & 0xFF].append(v)
        xs = [v for bucket in buckets for v in bucket]
    return xs


_STDLIB_PATTERN = bytes(range(256))


def stdlib_xxhash():
    return xxh64(_STDLIB_PATTERN * 8192, 0)


def stdlib_lz4():
    data = _STDLIB_PATTERN * 16384
    back = lz77_decompress(lz77_compress(data))
    return checksum64(back)


def stdlib_chacha20():
    key = bytes(range(32))
    nonce = bytes([0, 0, 0, 9, 0, 0, 0, 0x4A, 0, 0, 0, 0])
    ct = chacha20_encrypt(key, nonce, 1, _STDLIB_PATTERN * 4096)
    return checksum64(ct)


def stdlib_aho_corasick():
    patterns = ["needle" + str(i).zfill(4) for i in range(1000)]
    filler = "the quick brown fox jumps over the lazy dog "
    text = filler * 23000 + " ".join(patterns) + " "
    return multi_pattern_count(text, patterns)


def stdlib_radix_sort():
    keys = [(i * 2654435761) & 0xFFFFFFFF for i in range(100000)]
    return checksum64(radix_sort_u32(keys))


BENCHMARKS = {
    "fib": lambda: fib(32),
    "sieve": lambda: sieve(50000),
    "mandelbrot": lambda: mandelbrot(150, 100, 255),
    "nbody": lambda: nbody(5, 5000),
    "binary_trees": lambda: check_tree(make_tree(12)),
    "stdlib_xxhash": stdlib_xxhash,
    "stdlib_lz4": stdlib_lz4,
    "stdlib_chacha20": stdlib_chacha20,
    "stdlib_aho_corasick": stdlib_aho_corasick,
    "stdlib_radix_sort": stdlib_radix_sort,
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "fib"
    print(BENCHMARKS[name]())
